HOW TO RUN THE PROJECT:
1. Clone the repository to your local machine.
2. Open the project in your preferred IDE (e.g., Visual Studio Code, IntelliJ IDEA). The actual file that runs the application is the Dungeon_AI.ipynb jupyter notebook file in de project folder.
3. Install a venv
    1: Open Dungeon_AI and click select Kernel in the top-right
    2: Click 'Select another Kernel'
    3: Click 'Python Environments...'
    4: Click 'Create Python Environment'
    5: Click 'Venv' you don't need to install dependencies when asked.
    6: Open a powershell terminal in Visual Studio Code, make sure you are in the correct folder namely the root folder and type the following command:
        .\.venv\Scripts\Activate.ps1
    7: Now if you do the first step again, you should see the .venv you just created, select it

3. Make sure you have a .env file in the project folder with a variable named GOOGLE_API_KEY !!! 
    This is an api key for a gemini-2.0-flash API endpoint.
    You can make an gemini-2.0-flash api key on this website: https://aistudio.google.com/apikey
4. Make sure you have the required dependencies installed. There is a pip install in the first cell of the Dungeon_AI notebook. You need to run this.
5. Run the second cell in the Dungeon_AI jupyter notebook to start the game.
