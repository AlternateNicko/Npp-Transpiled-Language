# Terminal program for N++

import sys
sys.path.append("Npp")

from npp import NPP
from ndebug import debug

import os
import glob


npp = NPP("")
text = f"""
N++ Interactive Terminal Shell
Version {npp.version}
_______________________________________________________________
Type "help" for available commands
Type "n++" to run n++ intreperter shell
Type "n++ program.npp" to run an N++ code
"""


def load_path(directory_path, file_name):
    # Generate a list of all files with the specified file extension
    files = glob.glob(os.path.join(directory_path, file_name))
    
    # Return the first file found, or raise an error if no files are found
    return files[0]
    
commands = [
"help", "n++",
"cd", "ls", "dir", "mkdir",
"npi", 
]
path = "/storage/emulated/0"
os.chdir(path)
print(text)

import os
import sys

class SimpleShell:
    def __init__(self):
        self.cwd = os.getcwd()

    def run_interpreter(self):
        print("\nN++ Interactive Intrepreter")
        code = ""
        tab = 0
        while True:
            line = input(">>> ")
            if line == "exit":
                break
            if line == "check":
                print(code)
                continue
            if line == "clear":
                code = ""
                continue
            if line == "run":
                code = "\n"
                npl = NPP(code, {})
                result = npl.execute()
                continue
            if line == "save":
                path = input("Save Path Directory >>> ")
                with open(path, "w") as save_file:
                    save_file.write(code)
            elif line == "load":
                path = input("Load Path Directory >>> ")
                with open(path, "r") as load_file:
                    code = load_file.read()
            
            else:
                if line.startswith("{") and "}" not in line or line.endswith("{") and "}" not in line:
                    tab += 1
                if line.startswith("}") and "{" not in line or line.endswith("}") and "{" not in line:
                    tab -= 1
                code += " " * tab
                code += line + "\n"
                
    def run(self):
        print(f"Current Directory: {self.cwd}")
        while True:
            command = input("Enter command: ")
            if command.strip() == "exit":
                print("Exiting shell...")
                break
            elif command.strip() == "cd":
                new_path = input("Enter directory path: ")
                try:
                    os.chdir(new_path)
                    self.cwd = new_path
                    print(f"Changed directory to: {self.cwd}")
                except FileNotFoundError:
                    print("Directory not found.")
            elif command.strip() == "mkdir":
                directory = input("Enter the name of the directory")
                os.makedirs(directory, exist_ok=True)
                
            elif command.startswith("n++"):
                arg = command[3:].strip()
                if arg == "" or arg is None:
                    self.run_interpreter()
                else:
                    file_name = arg
                    if not arg.endswith((".npp", ".py", ".txt")):
                        print(f"Cannot process {arg} as it has a different file type unrelated to .npp")
                    try:
                        file_path = load_path(path, file_name)
                        with open(file_path, "r") as file:
                            code = file.read()
                        npp = NPP(code)
                        results = npp.execute()
                    except Exception as e:
                        print(e)
            elif command.strip() == "help":
                print("Available commands:\n")
                print("""
- help
- exit
- n++ [.npp]
- ls
- cd [directory]
                """)
            else:
                try:
                    result = os.system(command)
                    print(f"Result: {result}")
                except Exception as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    shell = SimpleShell()
    shell.run()