
class debug():
    def __init__(self, bool_debug):
        self.debug = bool_debug
    
    def print_functions(self, code):
        if not self.debug:
            return
        
        self.npp = code
        print(f"\nDEB: [ functions: ")
        if self.npp.functions:
            for name in self.npp.functions:
                print()
                print(name)
                for f in self.npp.functions[name]:
                    if "block" in f:
                        print("code")
                        tabs = 0
                        for i, c in enumerate(self.npp.functions[name][f]):
                            if c.endswith("}") or c.startswith("}"):
                                tabs -= 1
                            c = ("    " * tabs) + c
                            print(f"{i:<3}", ">>>", c)
                            if c.endswith("{") or c.startswith("{"):
                                tabs += 1
                              
                    else: print(f + ":", self.npp.functions[name][f])
        print("]")
    
    
    def types(self, value, mode="p"):
        if mode == "p":
            return type(value)
        if mode == "c" or mode == "clear" or mode == "clean":
            if isinstance(value, str):
                return "string"
            elif isinstance(value, int):
                return "int"
            elif isinstance(value, float):
                return "float"
            elif isinstance(value, list):
                return "list"
            elif isinstance(value, tuple):
                return "tuple"
            elif isinstance(value, dict):
                return "dict"
            elif isinstance(value, set):
                return "set"
            else:
                # supports any type
                new_type = str(type(value)).split(" ", 1)[1][1:-2]
                return new_type
                
    def print_classes(self, code):
        if not self.debug:
            return
        self.npp = code
        print("\nDEB: [ classes")
        if self.npp.classes:
            for name in self.npp.classes:
                print(name)
                for f in self.npp.classes[name]:
                    print(self.npp.classes[name][f])
        print("]")
        
    def print_init(self, code):
        if not self.debug:
            return
        self.npp = code
        print(f"\n\n—Debug—————————————————————————————————————————————————————————\
        \nDEB: [ Variables:")
        for i in self.npp.variables:
            print(f"{str(self.types(self.npp.variables[i])):<10} {str(i)+':':<10}{str(self.npp.variables[i])}")
    
    def print_libraries(self, code):
        if not self.debug:
            return
        self.npp = code
        print("_______________________________________________________________")
        print("DEB: [ Libraries:\
        \nName       |Root library| module")
        for imported, name in zip(self.npp.library, list(self.npp.library_name.values())):
            print(f"{name:<10} | {imported:<10} | {None if imported not in list(self.npp.nplibs.keys()) else self.npp.nplibs[imported]}")