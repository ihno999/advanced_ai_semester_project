from IPython.display import display, clear_output, Markdown
import json
import os
import google.generativeai as genai
import re
import ipywidgets as widgets
from dotenv import load_dotenv
from globals_variables import *
from item_stats import ( item_stat_boosts )
from magic_spells import magic_spells


# --- TRACK STAMINA LOSS DURING ACTIONS ---
def handle_stamina_loss(action_type):
    global player_stats
    
    if action_type in ["attack", "run", "defend", "dodge"]:
        # Deduct stamina when attacking or running
        stamina_cost = 10
        player_stats["stamina"] = max(0, player_stats["stamina"] - stamina_cost)
        return True
    return False


# --- REGENERATE STAMINA ---
def regenerate_stamina():
    global player_stats
    max_stamina = player_stats.get("max_stamina", 100)
    current_stamina = player_stats.get("stamina", 0)

    if current_stamina < max_stamina:
        # If the player is within 2 stamina points of max stamina, regenerate only what is needed.
        if max_stamina - current_stamina <= 2:
            player_stats["stamina"] = max_stamina
        else:
            player_stats["stamina"] = min(current_stamina + 5, max_stamina)


# --- CAST MAGIC SPELL ---
def handle_spell_casting(player_input):
    for spell_name in magic_spells:
        if spell_name.lower() in player_input.lower():
            spell = magic_spells[spell_name]
            mana_cost = spell["mana_cost"]
            if player_stats["mana"] >= mana_cost:
                player_stats["mana"] -= mana_cost
                return f"✨ **You cast _{spell_name}_**!\nEffect: {spell['effect']}\n🪄 Mana remaining: {player_stats['mana']}"
            else:
                return f"❌ Not enough mana to cast _{spell_name}_! You need {mana_cost}, but only have {player_stats['mana']}."
    return None  # No spell found in input


# --- REGENERATE MANA ---
def regenerate_mana():
    global player_stats
    max_mana = player_stats.get("max_mana", 50)  # Default max_mana if not defined
    current_mana = player_stats.get("mana", 0)

    if current_mana < max_mana:
        # If the player is within 2 mana points of max, regenerate only what is needed
        if max_mana - current_mana <= 2:
            player_stats["mana"] = max_mana
        else:
            player_stats["mana"] = min(current_mana + 2, max_mana)



# --- EQUIPMENT SLOT DETECTION ---
def detect_equipment_slot(item_name):
    name = item_name.lower()

    # Right hand items (sword, dagger, etc.)
    right_hand_items = ["sword", "dagger", "mace", "axe", "blade", "stick", "staff", "spear", "whip", "wand"]
    if any(w in name for w in right_hand_items):
        return "right_hand"

    # Left hand items (shield, buckler, torch, etc.)
    left_hand_items = ["shield", "buckler", "torch", "lamp", "light", "torchlight"]
    if any(w in name for w in left_hand_items):
        return "left_hand"

    # Helmet items (helmet, helm, hood, etc.)
    helmet_items = ["helmet", "helm", "hood", "cap", "mask", "headgear", "crown", "headpiece"]
    if any(w in name for w in helmet_items):
        return "helmet"

    # Chestplate items (chest, armor, robe, etc.)
    chestplate_items = ["chestplate", "armor", "robe", "shirt", "tunic", "vest", "plate", "body armor"]
    if any(w in name for w in chestplate_items):
        return "chestplate"

    # Leggings items (leggings, pants, greaves, etc.)
    leggings_items = ["leggings", "pants", "greaves", "trousers", "shorts", "skirt", "bottoms"]
    if any(w in name for w in leggings_items):
        return "leggings"

    # Boots items (boots, shoes, sandals, etc.)
    boots_items = ["boots", "shoes", "sandals", "footwear", "slippers", "sneakers", "kicks"]
    if any(w in name for w in boots_items):
        return "boots"

    # Accessories (ring, amulet, necklace, charm, locket)
    accessory_items = ["ring", "amulet", "necklace", "charm", "locket", "brooch", "bracelet", "trinket", "talisman", "pendant", "earring", "gemstone", "jewel"]
    if any(w in name for w in accessory_items):
        if not equipment["accessory_1"]:
            return "accessory_1"
        elif not equipment["accessory_2"]:
            return "accessory_2"
        else:
            return "accessory_1"  # Overwrite accessory_1 as fallback

    return None


# --- CALCULATE TOTAL STATS WITH EQUIPMENT ---
def calculate_total_stat(stat_name):
    base = player_stats.get(stat_name, 0)
    boost = 0
    for item in equipment.values():
        if item and item in item_stat_boosts:
            boost += item_stat_boosts[item].get(stat_name, 0)
    return base + boost



# --- XP AND LEVELING SYSTEM ---
def xp_required(level):
    return 20 + (level - 1) * 15

def check_level_up():
    global awaiting_stat_allocation
    level = player_stats.get("level", 1)
    xp = player_stats.get("xp", 0)
    max_xp = player_stats.get("max_xp", 20)
    leveled_up = False
    new_points = 0

    while xp >= max_xp:
        xp -= max_xp
        level += 1
        player_stats["max_health"] += 10
        player_stats["health"] = player_stats["max_health"]
        new_points += 1
        max_xp = xp_required(level)
        leveled_up = True

    player_stats["xp"] = xp
    player_stats["level"] = level
    player_stats["max_xp"] = max_xp
    player_stats["unassigned_stat_points"] = player_stats.get("unassigned_stat_points", 0) + new_points

    if leveled_up:
        awaiting_stat_allocation = True
        with output_area:
            clear_output()
            print_game_state()
            display(Markdown(f"🎉 **Level Up!** {player_name} reached level {level}!"))
        # prompt_stat_allocation()


# --- STAT ALLOCATION ---
def prompt_stat_allocation():
    global awaiting_stat_allocation
    unassigned = player_stats.get("unassigned_stat_points", 0)
    if unassigned <= 0:
        awaiting_stat_allocation = False
        return

    awaiting_stat_allocation = True
    options = ["Strength", "Defense", "Intelligence", "Endurance", "Magic"]
    stat_dropdown = widgets.Dropdown(options=options, description="Add to:")
    confirm_button = widgets.Button(description="Apply Point", button_style='success')

    # Define the function to handle the button click event
    def assign_stat(b):
        global awaiting_stat_allocation
        stat = stat_dropdown.value.lower()
        player_stats[stat] = player_stats.get(stat, 0) + 1

        # Bonus effects based on stat
        if stat == "endurance":
            player_stats["max_stamina"] += 5
            player_stats["stamina"] = player_stats["max_stamina"]
        elif stat == "magic":
            player_stats["max_mana"] += 5
            player_stats["mana"] = player_stats["max_mana"]

        player_stats["unassigned_stat_points"] -= 1

        # Re-render the updated game state and hide the stat allocation options
        with output_area:
            clear_output()  # Clear the current display
            print_game_state()  # Re-render the game state with updated stats
            display(Markdown(f"🧠 **Stat allocation complete!**"))
            display(input_box, submit_button)  # Re-display the input and submit button
            if player_stats["unassigned_stat_points"] > 0:
                display(Markdown(f"🧠 You have **{player_stats['unassigned_stat_points']}** stat point(s) left!"))
                display(stat_dropdown, confirm_button)  # Allow more allocation if points remain
            else:
                awaiting_stat_allocation = False  # Mark allocation as complete

    # Connect the button's click event to the `assign_stat` function
    confirm_button.on_click(assign_stat)

    # Create a separate page for stat allocation
    with output_area:
        clear_output()  # Clear previous page
        print_game_state()  # Optional: Display game context
        display(Markdown(f"🧠 You have **{unassigned}** unassigned stat point(s)! Choose a stat to upgrade:"))
        display(stat_dropdown, confirm_button)  # Display stat allocation interface


# --- STORY GENERATION ---
def generate_story(context, player_input, difficulty, player_stats, inventory, equipment):
    prompt = (
        "You are a fantasy dungeon-master AI. "
        "Continue the adventure in a vivid, immersive style. "
        "Do not repeat the player's action. Keep it concise (max 5 sentences). "
        "Make it interactive, try and end the output with a question so that the player can react to it. "
        "After the story, provide any game state updates (health, gold, inventory, xp) in this JSON format:\n"
        "`<META>{\"health\": -10, \"gold\": +5, \"xp\": 10, \"inventory_add\": [\"amulet\"], \"inventory_remove\": [\"torch\"], \"equip\": {\"right_hand\": \"iron sword\"}, \"unequip\": [\"helmet\"]}</META>`\n"
        "If no update is needed, just write `<META>{}</META>`.\n"
        "**All items, including loot and equipables, must come from the `item_stats.py` file. Do not invent new items.**\n"
        "**Any item meant for equipping must clearly correspond to one of these slots: `left_hand`, `right_hand`, `helmet`, `chestplate`, `leggings`, `boots`, `accessory_1`, or `accessory_2`.**\n"
        "Make sure equipped items are placed in the correct slot in the `equip` field of the JSON.\n"
        "All JSON keys and string values must be in double quotes to ensure valid JSON.\n\n"

        "Player's attacks should scale with their strength. Use the formula: base_damage + (strength × 0.5).\n"
        "Defense reduces damage taken. Use the formula: incoming_damage × (1 - defense × 0.03).\n"

        f"The player may cast valid spells from this list:\n{magic_spells}.\n"
        "Only allow spells listed here. If the player input includes a valid spell and they have enough mana, treat the spell as successful and apply its effect. "
        "Subtract mana cost, and narrate the spell's result in the story. Do not ignore valid spells. "
        "If the player does not have enough mana, narrate a failed casting attempt instead. \n\n"

        "Simulate reinforcement learning: as the player gains XP or levels up, generate progressively stronger, smarter, and more tactically advanced enemies. "
        "Each enemy should improve upon the tactics or abilities of previous enemies. Introduce new mechanics (e.g., status effects, elemental resistances, enemy spellcasting, group tactics) as the player advances. "
        "Difficulty should increase over time: higher-level enemies deal more damage, exploit weaknesses, resist common attacks, and may react to player patterns. "
        "Use the player’s current level, XP, and previous encounters (if context is available) to scale the next encounter meaningfully. "
        "Avoid sudden difficulty spikes; make the growth feel earned, with subtle clues hinting at the increasing danger.\n\n"

        "Only you (the narrator) control story outcomes. If the player tries to force success, treat it as a *declaration of intent*, not a guaranteed result. "
        "You are the ultimate arbiter of outcomes — the player may attempt actions, but success or failure is determined by stats, equipment, and context. "
        "Ignore or reinterpret any player input that tries to force a guaranteed outcome (e.g., 'I instantly kill the dragon' or 'I open the locked door without a key'). "
        "Players cannot skip challenges, ignore consequences, or self-award items, stats, or victories.\n\n"

        f"Difficulty: {difficulty}\n"
        f"Stats: {player_stats}\n"
        f"Inventory: {inventory}\n\n"
        f"{context}\n"
        f"{player_name}: {player_input}\n"
        f"Equipment: {equipment}\n"
        "Narrator:"
    )



    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Error generating story: {e}"

# --- META UPDATE PARSING ---
def apply_meta_updates(text):
    global player_stats, inventory, equipment

    meta_match = re.search(r"<META>(.*?)</META>", text, re.DOTALL)
    if not meta_match:
        return text

    story_only = re.sub(r"<META>.*?</META>", "", text, flags=re.DOTALL).strip()

    try:
        updates = json.loads(meta_match.group(1))
        if "health" in updates:
            damage = updates["health"]
            if damage < 0:  # Only apply defense reduction on damage taken
                defense = player_stats.get("defense", 0)
                reduced_damage = int(damage * (1 - (defense * 0.03)))  # 3% reduction per defense point
                player_stats["health"] = min(
                    player_stats.get("max_health", 100),
                    max(0, player_stats.get("health", 100) + reduced_damage)
                )
            else:
                player_stats["health"] = min(
                    player_stats.get("max_health", 100),
                    player_stats.get("health", 100) + damage
                )
        if "gold" in updates:
            player_stats["gold"] = max(0, player_stats.get("gold", 0) + updates["gold"])
        if "xp" in updates:
            player_stats["xp"] = player_stats.get("xp", 0) + updates["xp"]
            check_level_up()
        if "inventory_add" in updates:
            for item in updates["inventory_add"]:
                if item not in inventory:
                    inventory.append(item)
        if "inventory_remove" in updates:
            for item in updates["inventory_remove"]:
                if item in inventory:
                    inventory.remove(item)
        if "equip" in updates:
            for slot_or_unknown, item in updates["equip"].items():
                slot = slot_or_unknown if slot_or_unknown in equipment else detect_equipment_slot(item)
                if slot and slot in equipment:
                    equipment[slot] = item
                    if item in inventory:
                        inventory.remove(item)
                else:
                    story_only += f"\n\n⚠️ Couldn't determine correct slot for '{item}'."
        if "unequip" in updates:
            for slot in updates["unequip"]:
                if slot in equipment and equipment[slot]:
                    inventory.append(equipment[slot])
                    equipment[slot] = None

    except json.JSONDecodeError:
        story_only += f"\n\n❌ Error parsing meta update: Invalid JSON format."

    except Exception as e:
        story_only += f"\n\n❌ Error parsing meta update: {e}"

    return story_only

# --- GAME DISPLAY ---
def print_game_state():
    health = f"{player_stats.get('health', 0)}/{player_stats.get('max_health', 0)}"
    stamina = f"{player_stats.get('stamina', 0)}/{player_stats.get('max_stamina', 0)}"
    mana = f"{player_stats.get('mana', 0)}/{player_stats.get('max_mana', 0)}"
    strength = calculate_total_stat('strength')
    defense = calculate_total_stat('defense')
    intelligence = calculate_total_stat('intelligence')
    endurance = calculate_total_stat('endurance')
    magic = calculate_total_stat('magic')
    xp = f"{player_stats.get('xp', 0)}/{player_stats.get('max_xp', 0)}"
    level = player_stats.get('level', 1)
    gold = player_stats.get('gold', 0)

    def format_equipped(item):
        if item and item in item_stat_boosts:
            boosts = item_stat_boosts[item]
            boost_str = ", ".join(f"{k}+{v}" for k, v in boosts.items())
            return f"{item} ({boost_str})"
        return item or "None"

    equipped_items = "\n".join([
        f"- 🗡️ Right Hand: {format_equipped(equipment['right_hand'])}",
        f"- 🔦 Left Hand: {format_equipped(equipment['left_hand'])}",
        f"- ⛑️ Helmet: {format_equipped(equipment['helmet'])}",
        f"- 🛡️ Chestplate: {format_equipped(equipment['chestplate'])}",
        f"- 👖 Leggings: {format_equipped(equipment['leggings'])}",
        f"- 🥾 Boots: {format_equipped(equipment['boots'])}",
        f"- 📿 Accessory 1: {format_equipped(equipment['accessory_1'])}",
        f"- 📌 Accessory 2: {format_equipped(equipment['accessory_2'])}",
    ])

    display(Markdown(f"### 📖 **Story so far**\n{context}"))
    display(Markdown(
        f"**🧍 {player_name}'s Inventory:** {inventory}  \n"
        f"**❤️ Health:** {health}  |  **🏃‍♂️ Stamina:** {stamina}  |  **🔮 Mana:** {mana}  \n"
        f"**💪 Strength:** {strength}  |  **🛡 Defense:** {defense}  |  **🧠 Intelligence:** {intelligence}  |  **🦾 Endurance:** {endurance}  |  **✨ Magic:** {magic}  \n"
        f"**⭐ Level:** {level}  |  **🔹 XP:** {xp}  |  **💰 Gold:** {gold}  \n"
        f"🎯 Difficulty: {['Easy', 'Medium', 'Hard', 'Very Hard', 'Nightmare'][difficulty - 1]}\n\n"
        f"### 🧰 **Equipped Gear:**\n{equipped_items}"
    ))

# --- GAME TURN ---
def play_turn(player_input):
    global context

    if awaiting_stat_allocation:
        with output_area:
            clear_output()
            print_game_state()
            display(Markdown("⚠️ You must assign your unspent stat point(s) before continuing."))
            display(input_box, submit_button)
            prompt_stat_allocation()
        return

    if not player_input.strip():
        return

    # Handle stamina loss
    if handle_stamina_loss("attack" if "attack" in player_input.lower() else "run" if "run" in player_input.lower() else ""):
        with output_area:
            clear_output()
            print_game_state()
            display(Markdown(f"💨 **You lose 10 stamina** from {player_input}."))

    # Handle spell casting
    spell_result = handle_spell_casting(player_input)

    # Regenerate mana and stamina at end of turn
    regenerate_stamina()
    regenerate_mana()

    # Update game state
    game_memory.append(f"{player_name}: {player_input}")
    recent_context = "\n".join(game_memory[-6:])
    raw_output = generate_story(recent_context, player_input, difficulty, player_stats, inventory, equipment)
    cleaned_output = apply_meta_updates(raw_output)
    context_update = f"\n\n{cleaned_output}"
    context += context_update
    game_memory.append(cleaned_output)
    save_game()

    output_area.clear_output(wait=True)
    with output_area:
        print_game_state()
        if spell_result:
            display(Markdown(spell_result))
        display(Markdown("What does Ihno do next?"))
        display(input_box, submit_button)






# --- SAVE / LOAD / DELETE ---
def save_game():
    data = {
        "context": context,
        "game_memory": game_memory,
        "player_stats": player_stats,
        "inventory": inventory,
        "difficulty": difficulty,
        "equipment": equipment
    }
    with open(save_file, "w") as f:
        json.dump(data, f)

def load_game():
    global context, game_memory, player_stats, inventory, difficulty, equipment
    if not os.path.exists(save_file):
        with output_area:
            clear_output()
            display(Markdown("❌ No save file found!"))
        return
    with open(save_file, "r") as f:
        data = json.load(f)
    context = data["context"]
    game_memory = data["game_memory"]
    player_stats = data["player_stats"]
    inventory = data["inventory"]
    difficulty = data["difficulty"]
    equipment = data["equipment"]
    with output_area:
        clear_output()
        display(Markdown("✅ **Game loaded successfully!**"))
        print_game_state()
        display(input_box, submit_button)

def delete_save():
    if os.path.exists(save_file):
        os.remove(save_file)
    with output_area:
        clear_output()
        display(Markdown("🗑️ Save file deleted."))

# --- START NEW GAME ---
def start_new_game(difficulty_choice):
    global context, player_stats, inventory, difficulty, game_memory
    difficulty = {"Easy": 1, "Medium": 2, "Hard": 3}[difficulty_choice]
    base_stats = {
        "strength": 10, "defense": 0, "intelligence": 1, "endurance": 1, "magic": 1,
        "xp": 0, "level": 1, "max_xp": 20, "gold": 5,
        "max_health": 100, "max_stamina": 80, "max_mana": 30,
        "unassigned_stat_points": 0
    }

    if difficulty_choice == "Easy":
        base_stats.update({"health": 200, "max_health": 200, "strength": 15})
        inventory = ["Torch", "Wooden Sword"]
    elif difficulty_choice == "Medium":
        base_stats.update({"health": 100})
        inventory = ["Torch", "Wooden Stick"]
    elif difficulty_choice == "Hard":
        base_stats.update({"health": 50})
        inventory = ["Torch"]

    base_stats["health"] = base_stats.get("health", base_stats["max_health"])
    base_stats["stamina"] = base_stats["max_stamina"]
    base_stats["mana"] = base_stats["max_mana"]
    player_stats = base_stats

    context = f"{player_name} awakens in a dark forest. A mysterious figure approaches."
    game_memory = [context]
    save_game()
    with output_area:
        clear_output()
        display(Markdown(f"**New game started on _{difficulty_choice}_ difficulty.**"))
        print_game_state()
        display(input_box, submit_button)

# --- UI SETUP ---
input_box = widgets.Text(
    placeholder='What does Ihno do next?',
    description='▶️ Action:',
    layout=widgets.Layout(width='70%')
)
submit_button = widgets.Button(description="Submit", button_style='success')
submit_button.on_click(lambda b: (play_turn(input_box.value), setattr(input_box, "value", "")))

output_area = widgets.Output()

# --- GAME MENU ---
difficulty_dropdown = widgets.Dropdown(
    options=['Easy', 'Medium', 'Hard'],
    value='Medium',
    description='Difficulty:',
    layout=widgets.Layout(width='50%')
)
start_button = widgets.Button(description="New Game", button_style='primary')
load_button = widgets.Button(description="Load Game", button_style='info')
delete_button = widgets.Button(description="Delete Save", button_style='danger')

start_button.on_click(lambda b: start_new_game(difficulty_dropdown.value))
load_button.on_click(lambda b: load_game())
delete_button.on_click(lambda b: delete_save())