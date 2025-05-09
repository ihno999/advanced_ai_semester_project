# --- GLOBALS ---
model_name = "gemini-2.0-flash"
player_name = "Ihno"
context = ""
game_memory = []
player_stats = {}
inventory = []
difficulty = 1
save_file = "savegame.json"
awaiting_stat_allocation = False

equipment = {
    "left_hand": None,
    "right_hand": None,
    "helmet": None,
    "chestplate": None,
    "leggings": None,
    "boots": None,
    "accessory_1": None,
    "accessory_2": None
}