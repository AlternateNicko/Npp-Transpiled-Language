import re # for spliting characters or strings without striping it completly
import ast
import operator
from typing import Any, Dict, Union, List, Tuple, Set
import os
import copy
import sys as system
from pathlib import Path

if "Npp" not in system.path:
    system.path.append("Npp")
    from built_in_libraries import libraries

r = None
m = None
t = None
sys = None
json = None

# Define the safe operators you want to allow
allowed_operators: Dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.BitAnd: operator.and_,
    ast.BitOr: operator.or_,
    ast.BitXor: operator.xor,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
    ast.Invert: operator.inv,
    ast.And: all,
    ast.Or: any,
}

class SafeEval(ast.NodeVisitor):
    """
    Made my own eval, due to problems with pythons eval() function, since the language may run python code while evaluating normal expressions
    so this is a remake of python's eval without arbitrary python code executed, all of the things eval does are in here, just without arbitrary
    """
    def __init__(self, globals: Dict[str, Any] = None, locals: Dict[str, Any] = None) -> None:
        self.globals: Dict[str, Any] = globals or {}
        self.locals: Dict[str, Any] = locals or {}

    def visit(self, node: ast.AST, line = None) -> Any:
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        elif isinstance(node, ast.BinOp):
            left = self.visit(node.left)
            right = self.visit(node.right)
            return allowed_operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self.visit(node.operand)
            if isinstance(node.op, ast.UAdd):  # Unary positive
                return +operand
            elif isinstance(node.op, ast.USub):  # Unary negative
                return -operand
            return allowed_operators[type(node.op)](operand)
        elif isinstance(node, ast.Constant):  # For Python 3.8 and above
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in self.locals:
                return self.locals[node.id]
            elif node.id in self.globals:
                return self.globals[node.id]
            raise ValueError(f"Name '{node.id}' is not defined in `{line}`")
        elif isinstance(node, ast.BoolOp):
            values = [self.visit(value) for value in node.values]
            return allowed_operators[type(node.op)](values)
        elif isinstance(node, ast.Compare):
            left = self.visit(node.left)
            for operation, right in zip(node.ops, node.comparators):
                right = self.visit(right)
                if isinstance(operation, ast.Eq):
                    if left != right:
                        return False
                elif isinstance(operation, ast.NotEq):
                    if left == right:
                        return False
                elif isinstance(operation, ast.Lt):
                    if not left < right:
                        return False
                elif isinstance(operation, ast.LtE):
                    if not left <= right:
                        return False
                elif isinstance(operation, ast.Gt):
                    if not left > right:
                        return False
                elif isinstance(operation, ast.GtE):
                    if not left >= right:
                        return False
                elif isinstance(operation, ast.In):
                    if left not in right:
                        return False
                elif isinstance(operation, ast.NotIn):
                    if left in right:
                        return False
            return True
        elif isinstance(node, ast.List):
            return [self.visit(elt) for elt in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(self.visit(elt) for elt in node.elts)
        elif isinstance(node, ast.Set):
            return {self.visit(elt) for elt in node.elts}
        elif isinstance(node, ast.Dict):
            return {self.visit(key): self.visit(value) for key, value in zip(node.keys, node.values)}
        elif isinstance(node, ast.Subscript):  # Handling list/tuple indexing
            container = self.visit(node.value)
            index = self.visit(node.slice)
            if isinstance(container, (list, tuple)) and isinstance(index, int) or isinstance(container, (dict)) and isinstance(index, (int, str)):
                return container[index]
            raise ValueError(f"INDEX `{index}` `{container}` Invalid indexing: {ast.dump(node)} line `{line}`")
        elif isinstance(node, ast.Index):  # For subscript index
            return self.visit(node.value)
        else:
            raise ValueError(f"Unsupported operation: {ast.dump(node)} line {line}")
class NPP:
    def __init__(self, instructions, special_library={}, path=None, file="npp", extension=".npp"):
        # nplibs holds dictionaries like this
        # "lib_name": module_class,
        # where module_class is the class object of that library
        
        # CONFIGURATIONS
        self.version = "1.0.2" # current version
        self.path = Path.cwd() if path is None else path # current program directory
        self.file_name = file # name of file
        self.file_extension = extension
        self.run = True
        
        # LIBRARIES
        self.nplibs = special_library
        self.libraries = ["math", "time", "random", "smart", "sys", "files", "os"] # libraries, these are built ins
        self.libraries.extend(list(special_library.keys()))
        self.library = [] # library names will be appended here once they are imported
        self.nplibs_acc = {key: False for key in self.nplibs.keys()}

        # i may aswell explain each variables here
        self.Instructions = instructions.split("\n")# main instruction line gets split line by line
        
        self.variables = {} # all the variables are stored here
        self.return_val = None # return value
        self.bif = ["num", "input", "eval", "exec", "length", "sort", "min", "mean", "max", "median", "mode", "sum", "range", "call", "reverse", "type", "format",
            "zip", "dict", "map"
        ] # for eval to know if the expression they are evaluating has the languages codes
        self.bim = [] # this one is for methods
        self.cnt = 0 # the main pointer to the line of code
        self.output = [] # return output
        self.traceback = {"<module>": self.cnt} # the traceback, tracing back to where errors originate
        self.classes = {} # name: {methods: {method name: same as funcs}, variables: {name: value}, inheritence: [class name]
        self.og_c = 0 # the count, but the count where the pointer is pointing at, and not changed by any parsing actions
        self.in_smth = 0 # i forgot what this does
        self.in_if = False # inside an if statement
        self.if_executed = False # if an if statement is executed with the conditions being true, turns True
        self.condition = False # for the if, else if statement, turns true once their condition is also true
        self.in_block = 0 # while exiting or skipping some if and else if statement, this turns true if it's inside a code block (code blocks startimg with { and ends with })
        self.attempt = False # for try-except, but in this language is attempt-catch, once attempting to execute a code, all errors wont print out a trace back, instead it gets catch if it matches with the error name of the catch block
        self.special = "    " # for OOP, if a class constructor first argument is for example "self", this will be self, and if it's "fles" it will be fles :)
        self.in_class = [None, False] # if the program is currently in a code, first index stores the name of the class, the second shows True if they are in a class, else False
        self.arg = None # ngl idk what this is used for
        self.original_var = None # original variable once calling a new function, the self.variables are replace with a new dictionary, and original_var stores the global variables
        self.in_func = 0 # if it's currently inside a function
        self.func_name = "" # name of current function it's inside
        self.exec_fl = 0 # if it's currently executing a loop (for loop or while loops)
        self.breaking = False # force break out loops
        self.evals = False # if it's currently evaluating something
        self.functions = {} # where all the functions get stored, their entire code blocks, starting line, ending line, local variables, and arguments
        self.class_callers = {} # kind of like when a variable stores the class's name, pretty muc like this
        self.global_var = {} # Every variables
        self.library_name = {} # where renamed library or current library names are stored
        self.name_library = {} # Vice versa
        self.forbiden_chars = [" ", "'", '"', "(", ")", "[", "]", "{", "}", "~", "`", "@", "*", "+", "<", ">", "%", "#", "!", "?", ",", ":", ";", "/"] # characters forbiden to non string names
        self.sync_variables = {} # supports multiple syncronized variables instead of one
        self.func_scope = {} # contains the variables and other user defined values like functions and classes
        self.og_fname = "" # contains original function scope name or past name
        self.is_priv = False # private func
        self.is_pub = False # public func, both will be false if they are not inside one
        self.is_return = False # for return
        self.current_func = "" # current function
        self.eval_deb = False # for debug
        self.cache = {
            "eval": {}, # for evaluation
            "func": {},
            "class": {},
            "cond": {}, # for conditions
        } # the cache
        self.constants = {} # assign variable names if they are constant or not, becomes False if they are assigned
        self.Errors = { # all of the errors that will show up, if one of this is True, the whole code is stop and prints a trace back where the error originated,
            'SyntaxError': False,
            'IndexError': False,
            'RecursionError': False,
            'NameError': False,
            'ZeroDivisionError': False,
            'TypeError': False,
            'KeyError': False,
            'MemoryError': False,
            'ValueError': False,
            'ModuleError': False,
            'QuitError': False
        }
        
    def single_eval(self, expression, globals=None, locals=None):
        # evaluates one expression
        tree = ast.parse(expression.strip(), mode='eval')
        evaluator = SafeEval(globals, locals)
        self.evals = False
        return evaluator.visit(tree.body)
                        
    
    def eval(self, expression, globals=None, locals=None, arb=True, from_lib=False, from_exp=False):
        self.evals = True # a flag to tell the parser that is just evaluating
        # this eval has the ability to not just evaluate 1 expression, but multiple expressions, the language arbitrary codes, and more
        """Process of how eval handles an expression like
        variable = sum(var1) / length(var1) + var2 + mean(var3)
        first -> assign_variable first process the line, splits variable as "left" and the expression as "right"
        which then gets converted to "main" line after a few process
        after finding no simple matching expression, it feeds it to self.eval
        which the expression is now just sum(var1) / length(var1) + var2 + mean(var3)
        
        self.eval checks if it is a singular method (a function with a method without being too complex)
        self.eval splits the expression by "+" "-" "/" and "*", spliting each function as one
        breaking down the expression to "sum(var1)" "/" "length(var1)" "+" "var2" "+" "mean(var3)"
        then for the functions, it gets looped back to self.assigned variable, but this time as one function
        instead of multiple functions
        """
        if self.eval_deb:
            print("<NDB> EXPRESSION:", expression)
        
        # gets expression form
        if expression in self.variables.keys():
            return self.variables[expression]
        if not from_exp:
            expr = self.expression(expression)
            if expr["iseval"]:
                return eval(str(expr["expr"]), {}, self.variables) # This only evaluates NPP expression despite using python eval(),
                # self.expression() uses Npp approve and only syntax, doesn't include python codes'
            else:
                expression = expr["expr"]
        if from_lib:
            past_vars = copy.deepcopy(self.variables)
            self.variables = locals
        
        # this part processes dictionary key and values for the self.eval item processing (yes, eval uses itself)
        is_dict = self.special_find(expression, ":", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
        if len(expression) == 2 and self.expect(expression, (("(", ")"), ("[", "]"), ("{", "}"))):
            return self.single_eval(expression, globals, locals)
        if is_dict:
            exp = self.special_split(expression, ":", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"), limit=1)
            key = exp[0].strip()
            value = str(self.eval(exp[1].strip(), {}, self.variables))
            return (key, value)
        if arb:
            execution = False
            methods = False
            if expression.startswith(self.special) and self.in_class[1] and len(expression) > len(self.special + "."):
                execution = True
            if "." in expression and not expression.startswith(self.special):
                istrue = self.special_find(expression, ".", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                pattern = r'(?<!\w)[+-]?(?:\d+\.\d+|\d+\.|\.\d+)(?!\w)'
                if bool(re.search(pattern, expression)) and istrue:
                    execution = True
                elif not bool(re.search(pattern, expression)) and istrue:
                    execution = True
                    methods = True
            for i in self.bif: #
                if i in expression:
                    if "." + i in expression:
                        continue
                    execution = True
            if execution:
                v = False
                things = ["+", "-", "**", "*", "%", "/", "<=", ">=", "<", ">", "==", "!="]
                v = self.special_find(expression, things, ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                # processes item expressions
                if expression.strip().startswith(("(", "[", "{")):
                    expr = expression[:1]
                    expression, cnt = self.get_items(expr, expression)
                    new = ""
                    for ex in expression:
                        new += ex
                    expression = new
                    if_item = self.special_find(expression, ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                    if expression.startswith("(") and expression.endswith(")") and not if_item:
                        expression = expression[1:-1]
                    else:
                        item_types = {
                            "[": "list",
                            "(": "tuple",
                            "{": "dictionary"
                        }
                        ending = {
                            "[": "]",
                            "(": ")",
                            "{": "}" 
                        }
                        line = expression[:1]
                        end_line = ending[line]
                        i_type = item_types[line]
                        expression = self.special_split(expression[1:-1], ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                        vals = []
                        txt = ""
                        for ex in expression:
                            if i_type == "dictionary":
                                dicts = self.eval(ex, {}, self.variables)
                                vals.append(dicts[0] + ": " + dicts[1])
                            else:
                                vals.append(str(self.eval(ex, {}, self.variables)))
                        # reconstruct
                        new = line
                        for v in vals:
                            new += v + ", "
                        new += end_line
                        expression = new
                if v:
                    org = expression
                    expression = self.ultimate_split(expression, things)
                    chars = []
                    cnt = 0
                    while cnt != len(expression):
                        if expression[cnt] in things:
                            v = expression[cnt]
                            del expression[cnt]
                            chars.append(v)
                            cnt -= 1
                        cnt += 1
                    vals = []
                    for ex in expression:
                        # please don't tell me why it is like this
                        self.assign_variable("<<temporary_variable>> = " + ex, methods) # this class method includes handling variable assignments and the functions for arbitrary
                        expression = self.variables["<<temporary_variable>>"] # the name of the variable is like this because this may delete a existing variable that may have this name
                        vals.append(str(expression))
                    del self.variables["<<temporary_variable>>"] # it deletes it
                    final = ""
                    for v, c in zip(vals, chars):
                        final += v + " " + c + " " # puts all of the evaluated expressions, arithmetic characters back to one string to be executed one last time
                    final += vals[-1]
                    expression = final
                else:
                    try:
                        if self.special in expression and self.in_class[1]:
                            name_var = expression
                            
                            if name_var in self.classes[self.in_class[0]]["variables"].keys():
                                
                                v = self.classes[self.in_class[0]]["variables"][name_var]
                                return v
                        return self.eval(expression.strip(), {}, self.variables, arb=False)
                    except Exception as e:
                        if self.special in expression and self.in_class[1] and expression in self.classes[self.in_class[0]]["variables"].keys():
                            name_var = expression
                            return self.classes[self.in_class[0]]["variables"][name_var]
                        
                        self.assign_variable("<<temporary_variable>> = " + expression.strip(), methods) # if the expression doesn't contain any arithmetic characters (+ * - /), it runs this
                        expression = self.variables["<<temporary_variable>>"]
                        expression = str(expression)
                        del self.variables["<<temporary_variable>>"]
                        
        expression = str(expression)
        tree = ast.parse(expression.strip(), mode='eval') # parsing time
        evaluator = SafeEval(globals, locals)
        self.evals = False
        if from_lib: self.variables = past_vars
        return evaluator.visit(tree.body, expression) # final evaluator
    
    def expression(self, exp):
        # My attempt of a eval rework - Current exprience me
        """
        Converts expressions written in Npp into a AST readable form that can be run in self.eval or instantly to evaluation
        Why did i write this?
        - because repitition of if, else if statements, while loops are slow due to recursion calls of self.eval -> self.assign_variable...

        important variables:
            self.cache
            self.constants
            self.variables
        
        can be run with either self.eval() or eval()
        this function returns a dictionary, this contains
        {
            "expr": exp, "iseval": bool, "variables": {"name": True, "name2": False}
        }
        which is then saved in self.cache
        booleans in variables means if its constant or not during it's first evaluation'
        """
        # cache loading
        if exp in self.cache["eval"].keys():
            change = True
            for v in self.cache["eval"][exp]["variables"].keys():
                if self.cache["eval"][exp]["const"][v][0] != self.constants[v][0]:
                    change = False
                    break
            if change:
                return self.cache["eval"][exp]
        
        # main parser converter
        """
        goal: Finds variables inside the expression and checks if that variable is constant or not
        constant variables: constant variables gets its values fetched immidietly into the expression,
        since it stays constant, values are never changed
        non-constants: non-constant variables never gets its values fetched since the variable is changed after evaluation
        
        if it's a simple expression after converting (like just 60 + 20, or 10 == 20) it immidietly evaluates
        only returns expression forms if only there is
        - unfetched non constant variables
        - arbitrary Npp expressions (like built ins)
        """
        iseval = False
        expression = {"expr": None, "iseval": iseval, "variables": {}, "const": copy.deepcopy(self.constants)}
        variables = {}
        # example: cnt == length(list), should return cnt == 60 (cnt is non constant, list is)
        if any(v in exp for v in self.variables.keys()): # checks if variables are inside the expression
            # uses the same technique as eval, split the expressions
            operators = ["+", "-", "**", "*", "%", "/", "<=", ">=", "<", ">", "==", "!="]
            final_exp = []
            has_built_ins = self.special_find(exp, operators, ("'", '"', "(", "{", "["), ("'", '"', ")", "}", "]"))
            if not has_built_ins:
                expression["expr"] = self.eval(exp, {}, self.variables)
                expression["iseval"] = True
                var = exp
                if self.special_find(exp, ".", ("'", '"', "(", "[", "{"), ("'", '"', ")", "]", "}")):
                    var = exp.split(".", 1)[0].strip()
                    
                expression["variables"][var] = True if var in self.constants.keys() and self.constants[var][0] else False
                
            else:
                lines = self.ultimate_split(exp, operators)
                # goes through each one to check each variables
                operator = []
                cnt = 0
                # splits expressions away from operators
                while cnt != len(lines):
                    if lines[cnt] in operators:
                        operand = lines[cnt]
                        del lines[cnt]
                        operator.append(operand)
                        cnt -= 1
                    cnt += 1
                for line in lines:
                    if any(i + "(" in line for i in self.bif):
                        # tricky, since it needs to check if variable is actually constant or not while that variable is inside a parenthesis
                        # while that, there is also nested functions like median(sort(list))
                        main_line = line
                        while True:
                            line = line.split("(", 1)[1].removesuffix(")").strip() # removes function
                            if not any(i in line for i in self.bif):
                                break
                        # now checks that line if it's constant or not, if it is then evaluate main line
                        if line.strip() in self.constants.keys() and line in self.variables.keys() and self.constants[line][0]:
                            final_exp.append(str(self.eval(main_line, {}, self.variables)))
                            variables[line] = True
                        # else it loads main line
                        else:
                            final_exp.append(main_line)
                            variables[line] = False
                    elif line in self.constants.keys() and line in self.variables.keys() and self.constants[line][0]:
                        # means constant, constant = load it in
                        final_exp.append(str(self.variables[line]))
                        variables[line] = True
                    else:
                        final_exp.append(line)
                        if line in self.variables.keys():
                            variables[line] = False
                expr = ""
                for v, c in zip(final_exp, operator):
                    expr += v + " " + c + " "
                expr += final_exp[-1]
                expression["expr"] = expr
                expression["iseval"] = has_built_ins
                expression["variables"] = variables
                
        else: # means it's instantly evaluated
            expression["expr"] = self.single_eval(exp, {}, self.variables)
            expression["iseval"] = True
            expression["variables"] = {}
        # save to cache
        self.cache["eval"][exp] = expression
        return expression
        
        
        
        
    def execute(self):
        # main executer of the code, the start up
        while True:
            if self.cnt >= len(self.Instructions):
                break # ends the program once the cnt reaches over the programs amount of line of code
            instruction = self.Instructions[self.cnt]
            self.traceback["<module>"] = self.cnt
            result = self.execute_functions(instruction) # parses the single line of code
            if result != None:
                print(result) # print results
            self.cnt += 1
            self.og_c += 1
            # Check for errors
            if True in self.Errors.values() and not self.attempt:
                quit()
        return
        
    def exec_block(self, code, count):
        # executes a code block, separate uses from the execute method
        self.cnt = 0
        ogc = self.og_c
        original = self.Instructions
        was_in = True if self.in_func else False
        self.Instructions = code.split("\n")
        
        while self.cnt < len(self.Instructions):
            instruction = self.Instructions[self.cnt].strip()
            if instruction == "":
                pass
            else:
                result = self.execute_functions(instruction)
                if result != None:
                    print(result)
            self.cnt += 1
            self.og_c += 1
            if self.in_func == 0 and was_in or self.is_return:
                break
            # Check for errors
            if True in list(self.Errors.values()):
                if not self.attempt: quit()
                break
        self.cnt = count
        self.og_c = ogc
        self.Instructions = original
        return self.output
    
    def prep_exec(self, code): # prepares to execute a code block
        final = ""
        for i in code:
            final += i + "\n"
        return final
    # get code block helper function
    # also supports getting nested blocks, and dont need indent because of the braces (and the rest)
    def get_block(self, intent=False):
        cnt = self.cnt
        if '{' in self.Instructions[cnt].strip() or "{" in self.Instructions[cnt + 1].strip():
            cnt += 1 if '{' not in self.Instructions[cnt] else 0 # for brackets starting at the same line as the function definition
            if "{" in self.Instructions[cnt]:
                nested = 1
                cnt += 1
            else:
                nested = 0
            block = [] # to be returned
            while cnt < len(self.Instructions):
                line = self.Instructions[cnt].strip()
                block.append(line)
                cnt += 1
                if self.special_find(line, "{", ("'", '"', "(", "["), ('"', "'", ")", "]")):
                    nested += 1
                if self.special_find(line, "}", ("'", '"', "(", "["), ('"', "'", ")", "]")):
                    nested -= 1
                    if nested == 0: # if nested is 1 (meaning is the main code block), it will break out of the loop snd return the block
                        break
                # else, the cnt is in the code block
            c = 0
            # pre process the codes for ending brackets
            line = block[-1]
            if line.strip().endswith("}") and not line.strip().startswith("}"):
                block[-1] = line.strip()[:-1].strip()
            elif line.strip() == "}":
                del block[-1]
            return block, cnt
        else:    
            
            print("\033[31mTraceback(most_recent_call_back):\033[0m")
            print(f"    TB-[ line: {self.cnt}, code: {self.Instructions[self.cnt]}")
            print("\nSyntaxError: no starting curly braces `{` at the start of an code block")
            self.Errors["SyntaxError"] = True
            return [], 0
   
    def process_vars(self):
        """
        runs each loop, this updates a class variable by the current scope variable (self.variables)
        and with the new feature "sync", it is now responsible for syncing the variables with the host or group variables
        based on the sync mode, and values of the synced variables.
        There would be more uses in the near future
        """
        for v in self.variables.keys():
            if v.startswith(self.special + ".") and self.in_class[1]:
                self.classes[self.in_class[0]]["variables"][v] = self.variables[v]
                if v not in self.classes[self.in_class[0]]["variables"]["<attr>"]:
                    self.classes[self.in_class[0]]["variables"]["<attr>"].append(v)
            if v not in self.constants.keys():
                self.constants[v] = [True, self.variables[v]]
            if self.variables[v] != self.constants[v][1]:
                self.constants[v][0] = False
            
            self.constants[v][1] = self.variables[v]
                
        if self.in_class[1]:
            self.classes[self.in_class[0]]["variables"]["<dict>"].update(self.classes[self.in_class[0]]["variables"])

        self.global_var.update(self.variables)
        
        # for sync variables
        if self.sync_variables == {}:
            return
        sync_groups = list(self.sync_variables.keys())
        for gr in sync_groups:
            group = self.sync_variables[gr].copy()
            for name in group["all"].keys():
                if name in self.variables.keys():
                    variables = {name: self.variables[name]}
                    self.sync_variables[gr]["past group value"] = self.sync_variables[gr]["group value"].copy()
                    self.sync_variables[gr]["group value"].update(variables)
                    self.sync_variables[gr]["all"].update(variables)
            if group["host"] in group["group value"].keys():
                del self.sync_variables[gr]["group value"][group["host"]]
            if group["host"] in group["past group value"].keys():
                del self.sync_variables[gr]["past group value"][group["host"]]
            if group["mode"] == "hva":
                # checks if host variables changed value
                host = group["host"]
                vars = group["group value"]
                self.sync_variables[gr]["past group value"] = vars.copy()
                host_val = self.variables[host]
                if host_val != group["past value"]:
                    new_var = {}
                    for vars in group["group"]:
                        self.variables[vars] = host_val
                        new_var[vars] = host_val
                    self.sync_variables[gr]["group value"] = new_var
                    self.sync_variables[gr]["past value"] = host_val
            elif group["mode"] == "avs":
                def sync_dict_values(d):
                    values = list(d.values())
                    first = values[0]
                
                    # Find a value that's different
                    different = None
                    for value in values[1:]:
                        if value != first:
                            different = value
                            break
                
                    if different is None:
                        return
                
                    # Copy the different value to every key
                    for key in d:
                        d[key] = different
                
                    return d
                vars = group["all"]
                self.sync_variables[gr]["past group value"] = vars.copy()
                new_dict = sync_dict_values(vars)
                self.sync_variables[gr]["group value"] = new_dict
                self.sync_variables[gr]["all"] = new_dict
                self.variables.update(new_dict)
            elif group["mode"] == "gva":
                # host changes values by their group value
                host = group["host"]
                vars = group["group value"]
                past = group["past group value"]
                host_val = self.variables[host]
                all_dict = group["all"]
                # checks if even one value matches
                value = None
                for key in vars.keys():
                    if vars[key] == past[key]:
                        continue
                    value = vars[key]
                    break
                if value is None:
                    pass
                else:
                    host_val = value
                    all_dict.update({host: host_val})
                    self.sync_variables[gr]["all"] = all_dict
                    self.variables.update(all_dict)
                    self.sync_variables[gr]["past group value"] = vars.copy()
            
    
    def get_items(self, types, line=None):
        """
        uses the same codes of self.get_block()
        except it handles lists, tuples, and dictionaries instead of code blocks
        """
        item_types = {
            "[": "list",
            "(": "tuple",
            "{": "dictionary"
        }
        ending = {
            "[": "]",
            "(": ")",
            "{": "}" 
        }
        
        item_type = item_types[types]
        item_end = ending[types]
        if line is not None and line.endswith(item_end):
            return [line], self.cnt
        cnt = self.cnt
        if types in self.Instructions[cnt]:
            nested = 1
            block = [] # to be returned as items
            line = self.Instructions[cnt].strip().split("=")[1].strip()
            block.append(line)
            cnt += 1
            while cnt < len(self.Instructions) and nested > 0:
                line = self.Instructions[cnt].strip()
                if line.startswith(types):
                    nested += 1
                if line.endswith(item_end):
                    nested -= 1
                    if nested == 0:
                        block.append(line)
                        cnt += 1
                        break
                block.append(line)
                cnt += 1
            if nested != 0:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                    print(f"\nTypeError: {item_type} cannot be created without an ending {item_end} bracket/parenthesis")
                    self.Errors["TypeError"] = True
                return [], 0
            return block, cnt
        else:
            
            print("\033[31mTraceback(most_recent_call_back):\033[0m")
            for i in self.traceback:
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `(<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nTypeError: Item can't be created")
                self.Errors["TypeError"] = True
            return None
        
    def num(self, value, numsys):
        """
        converts an interger to any type of number system,
        and a number system to any number system (and back to int)
        like
        int 10 -> bin 1010
        int 69 -> hex 45
        int 420 -> oct 644
        """
        if numsys == 'bin':
            return bin(value)[2:]
        elif numsys == 'hex':
            return hex(value)[2:]
        elif numsys == 'oct':
            return oct(value)[2:]
        else:
            if not self.attempt:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nValueError: {numsys} is an invalid number system type")
            self.Errors["ValueError"] = True
            return
    
    def convert_arg(self, args):
        """
        converts user defined function and method args
        by their types
        """
        if args.startswith('"') and args.endswith('"') or args.startswith("'") and args.endswith("'"):
            return args[1:-1]
        try:
            return self.eval(args, {}, self.variables)
        except Exception:
            return args
            
    def global_vars(self):
        globals = []
        for g, l in zip(self.variables.keys(), self.original_var.keys()):
            if g == l:
                globals.append(g)
        for i in globals:
            self.original_var[i] = self.variables[i]
    
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
        
    def run_condition(self, cond):
        """
        This function runs condition expressions used in while, if, and else if statements
        there are also logical operators with uses for the conditions, like
        && as "and", || as "or", ^^ as "xor", and "!" before parenthesis as "not"
        """
        arguments = self.ultimate_split(cond, ["&&", "||", "^^"]) # splits the condition by operators
        text = ""
        for args in arguments:
            if args.startswith(("(", "!(")):
                isnot = False
                if args.startswith("!"):
                    isnot = True
                expr = args[2:-1].strip() if isnot else args[1:-1].strip()
                expression = self.expression(expr)
                if expression["iseval"]: # instant evaluation, use eval() since there is no more arb code
                    boolean = eval(expression["expr"], {}, self.variables)
                else:
                    boolean = self.eval(expression["expr"], {}, self.variables, from_exp=True)
                if not isinstance(boolean, bool):
                    if not self.attempt:
                        print("\033[31mTraceback(most_recent_call_back):\033[0m")
                        for i in self.traceback:
                            print(f"    TB - [ File `(<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nTypeError: expected value type of condition is `bool` but got `{type(boolean)}`")
                            self.Errors["TypeError"] = True
                        return None
                if isnot:
                    if boolean:
                        boolean = False
                    else:
                        boolean = True
                text += str(boolean) + " "
            elif args in ["&&", "||", "^^"]:
                
                text += args[1:] + " "
        new_cond = self.eval(text, {}, self.variables)
        return new_cond
    
    def expect(self, line, parts=[]):
        i = 0
        condition = 0
        while i < len(parts):
            if not line.startswith(parts[i][0]) and line.endswith(parts[i][1]):
                condition += 1
            i += 1
        if condition == 0:
            return True
        return False
        
    def ultimate_split(self, line, split_tokens, group_pairs=(("'", '"'), ('"', "'")), nest_pairs=(("(", ")"), ("[", "]"), ("{", "}")), join_capture=True):
        """
        Splits 'line' by any of the split_tokens, ignoring tokens inside strings or nested groups.
        
        - split_tokens: list of strings to split by (can be multi-char)
        - group_pairs: string quote pairs
        - nest_pairs: parentheses/brackets/braces pairs
        
        """
        result = []
        current = ""
        stack = []  # stack for parentheses/brackets/braces
        in_string = None  # current quote character if inside a string
        i = 0
        while i < len(line):
            char = line[i]
    
            # String handling
            if in_string:
                current += char
                if char == in_string:
                    in_string = None
                i += 1
                continue
            elif any(char == start for start, end in group_pairs):
                in_string = char
                current += char
                i += 1
                continue
    
            # Nesting handling
            elif any(char == start for start, end in nest_pairs):
                stack.append(next(end for start, end in nest_pairs if start == char))
                current += char
                i += 1
                continue
            elif stack and char == stack[-1]:
                stack.pop()
                current += char
                i += 1
                continue
    
            # Split token check (multi-char)
            split_matched = False
            for token in split_tokens:
                if line[i:i+len(token)] == token and not stack and not in_string:
                    if current:
                        result.append(current.strip())
                    if join_capture:
                        
                        result.append(token)
                    current = ""
                    i += len(token)
                    split_matched = True
                    break
            if split_matched:
                continue
    
            # Normal character
            current += char
            i += 1
    
        if current:
            result.append(current.strip())
        return result
    def special_split(self, line, split_str, in_char1, in_char2, ret_capture_group=False, limit=None):
        """
    splits a string into a list by using split()
    and only splits the characters that's outside of a specific character
    like if it is outside ( and )
    
    why i add this? because problems like this
    
    output(range(10, 20, 2), sort(list1, True), len(range(0, 30, 3)))
    and i wanna split it by comma's
    but there is so many coma's
    it just ruins the function's arguments
    and supposed to output as ["range(10, 20, 2)", " sort(list1, True)", " len(range(0, 30, 3))"]
    but... normal .split() can't do that
    so i did this
        """
        new_line = ""
        inside_char = False
        i = 0
        splits = 0
    
        while i < len(line):
            # Check if we're inside quotes
            if line[i] in in_char1 and not inside_char:
                inside_char = line[i]
                new_line += line[i]
                i += 1
                continue
            elif line[i] in in_char2 and inside_char:
                inside_char = False
                new_line += line[i]
                i += 1
                continue
    
            # Check for the multi-character split
            if (
                not inside_char
                and (limit is None or splits < limit)
                and line[i:i + len(split_str)] == split_str
            ):
                new_line += (
                    "¤"
                    if not ret_capture_group
                    else f"¤{split_str}¤"
                )
                splits += 1
                i += len(split_str)
                continue
    
            # Otherwise, just copy character
            new_line += line[i]
            i += 1
    
        if "¤" in new_line:
            return new_line.split("¤")
        return [new_line]
    
    def special_find(self, line, target, in_char1, in_char2):
        """
        This function works like special_split, but it returns True or False if target_str is in the string
        only if it exist, and is not inside the chosen characters (in_chars1 for the start and in_chars2 for the end)
        it has the same method as special_split, just a different purpose
        
        this function fixes the bug in self.eval() about running a built in method inside as an argument of an built in function (or even user defined)
        """
        inside_char = False
        i = 0
        if not isinstance(target, list):
            target = [target]
    
        while i < len(line):
            # Enter quoted section
            if line[i] in in_char1 and not inside_char:
                inside_char = line[i]
                i += 1
                continue
    
            # Exit quoted section
            elif line[i] in in_char2 and inside_char:
                inside_char = False
                i += 1
                continue
    
            # Check for target only when outside quotes, even multiple
            # if not inside_char and line[i:i+len(target)] == target:
            if not inside_char and any(line[i:i+len(t)] == t for t in target):
                return True
    
            i += 1
    
        return False
        
    def run_functions(self, name, provided_args, infunc):
        """
        runs a user defined function and process its arguments as variables,
        it also has a scope system where variables are refreshed but you can still access global variables
        the original variables in the main program are untouched
        """
        self.in_func += 1 # for nested function calls
        og_cond = self.is_priv
        og_cond1 = self.is_pub
        if not infunc:
            block = self.functions[name]['block']
            count = self.functions[name]['end']
            argument = provided_args
            arg = self.functions[name]['args']
            self.is_pub = True
            self.is_priv = False
        else:
            if self.func_name in self.func_scope.keys():
                block = self.func_scope[self.func_name]["functions"][name]['block']
                count = self.func_scope[self.func_name]["functions"][name]['end']
                arg = self.func_scope[self.func_name]["functions"][name]['args']
            else:
                block = self.func_scope[self.og_fname]["functions"][name]['block']
                count = self.func_scope[self.og_fname]["functions"][name]['end']
                arg = self.func_scope[self.og_fname]["functions"][name]['args']
            argument = provided_args
            self.is_priv = True
            self.is_pub = False
        self.cnt = 0
        point = self.cnt
        if len(argument) > len(arg):
            if not self.attempt:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")    
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nTypeError: Function `{name}` takes {len(arg)} amount of arguments, but {len(argument)} is given")
            self.Errors["TypeError"] = True
            return
        if '' in arg:
            del arg[0]
        self.traceback[name] = self.og_c
        self.original_var = self.variables
        self.variables = {}
        
        past_name = self.og_fname
        og_name = self.func_name
        og_cache = self.cache
        self.cache = {
            "eval": {}, # for evaluation
            "func": {},
            "class": {},
            "cond": {} # for conditions
        }
        self.og_fname = self.func_name
        self.func_name = name
        original_inst = self.Instructions
        for value, n in zip(argument, arg):
            self.variables[n.strip()] = value
            self.constants[n.strip()] = [True, value]
        self.process_vars()
        
        code = self.prep_exec(block)
        self.exec_block(code, count)
        self.global_vars()
        self.variables = self.original_var
        self.in_func -= 1
        if infunc:
            if self.func_name in self.func_scope.keys():
                self.func_scope[self.func_name]["variables"] = self.variables.copy()
            else:
                self.func_scope[self.og_fname]["variables"] = self.variables.copy()
        self.func_name = og_name
        self.og_fname = past_name
        self.original_var = {}
        self.Instructions = original_inst
        self.cnt = count
        self.cache = og_cache
        self.is_priv = og_cond
        self.is_pub = og_cond1
        del self.traceback[name]
        return
        
    def run_methods(self, name, m_name, provided_args, infunc):
        """
        almost the same code as run_function (because it is)
        but with a different responsibility... (which is just running user defined functions but cooler)
        """
        block = self.classes[name]["methods"][m_name]['block']
        count = self.classes[name]["methods"][m_name]['end']
        argument = provided_args
        arg = self.classes[name]["methods"][m_name]['args'].copy()
        self.special = arg[0] if m_name == "<const>" else self.special
        self.arg = arg
        self.cnt = 0
        self.func_name = name
        point = self.cnt
        if len(argument) > len(arg):
            if not self.attempt:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nTypeError: Class `{name}` Method `{m_name}` takes {len(arg)} amount of arguments, but {len(argument)} is given")
            self.Errors["TypeError"] = True
            return
        if '' in arg or self.special in arg:
            del arg[0]
        self.traceback[m_name] = self.og_c
        self.original_var = self.variables.copy()
        og_var = self.variables.copy()
        self.variables = self.classes[name]["variables"].copy()
        past_name = self.og_fname
        og_name = self.func_name
        og_cache = self.cache
        self.cache = {
            "eval": {}, # for evaluation
            "func": {},
            "class": {},
            "cond": {} # for conditions
        }
        self.og_fname = self.func_name
        self.func_name = name
        self.in_class[1] = True
        self.in_class[0] = name
        
        self.in_func += 1
        original_inst = self.Instructions
        for value, n in zip(argument, arg):
            self.variables[n.strip()] = value
            self.constants[n.strip()] = [True, value]
        for k in self.variables.keys():
            if k.startswith(self.special):
                self.classes[name]["variables"][k] = self.variables[k]
        self.process_vars()
        
        
        code = self.prep_exec(block)
        self.exec_block(code, count)
        if self.in_func == 0:
            
            self.variables = self.original_var
            self.variables.update(og_var)
            self.Instructions = original_inst
            self.cnt = count
            return self.return_val
        self.func_name = og_name
        self.og_fname = past_name
        self.global_vars()
        
        self.variables = self.original_var.copy()
        self.variables.update(og_var)
        self.in_func -= 1
        if self.in_func < 0:
            self.in_class = [None, False]
        self.cache = og_cache
        self.original_var = {}
        self.Instructions = original_inst
        self.cnt = count
        if name in self.traceback:
            del self.traceback[m_name]
        return
    
    def load(self, name, addr, value):
        """
        handles list assignments in the past, but now it both handles
        list assignments and dictionary assigmments
        """
        var = self.variables[name]
        addr = self.eval(addr, {}, self.variables)
        value = self.eval(value, {}, self.variables)
        if isinstance(var, (list, dict)):
            if isinstance(var, dict):
                self.variables[name][addr] = value
            elif int(addr) > len(var) or int(addr) is None:
                if not self.attempt:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                    print(f"\nIndexError: length of list {name} is `{len(var)}` but `{len(addr)}` is out of list range")
                self.Errors["IndexError"] = True
                return
            else:
                self.variables[name][int(addr)] = value
                return
        else:
            if not self.attempt:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nTypeError: Given variable {name} value is not a list -> type: {type(value)}")
                self.Errors["TypeError"] = True
            return
    
    def execute_functions(self, instruction):
        """where lines are processed through
        but further down the code, the lines breaks up into smaller and smaller peices
        where the code understands it with the help of other functions like
        self.assign_variable(), self.methods(), and self.evals()
        
        so that means there is a layer of parsing the program does instead of doing it by once
        this is the first layer, where lines are checked to where they should execute,
        this is where keywords are executed aswell, if keywords weren't checked, it checks if it's a variable assignment
        if not, it checks if it's using a built in method (without variable assignment)
        then checks if it's using a library function
        then only says SyntaxError
        
        Layer 1 of parsing
        """
        global m, r, t, json, sys
        
        if isinstance(instruction, list):
            instruction = instruction[0].strip()
        else:
            instruction = instruction.strip()
        if not instruction:
            pass
            
        elif instruction.startswith('//'): pass # programming language's comment syntax
                    
        elif instruction.startswith('ignore'):
            pass # passes instructions, usefull for placeholders
        
        elif instruction.startswith('output'):
            return self.handle_output(instruction) # stdout
            
        elif instruction.startswith('quit()'):
            self.Errors["QuitError"] = True # a hidden error just to stop the program without affecting the main python program
            return
        
        elif instruction.startswith('inherit ') and self.in_class[1]:
            arg = instruction[8:].strip().split(" from ", 1)
            method = arg[0].strip() # like <const>
            classes = arg[1].strip() # like Parent()
            arg = method[:-1].split('(', 1)
            method = arg[0].strip()
            argument = self.special_split(arg[1].strip(), ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
            c_class = copy.deepcopy(self.classes[self.in_class[0]])
            p_class = c_class["inherits"][c_class["inherits"].index(classes)]
            p_info = copy.deepcopy(self.classes[p_class])
            if method in p_info["methods"].keys():
                args = [self.convert_arg(arg.strip()) for arg in argument]
                self.classes[p_class]["methods"]["<const>"]["end"] = self.cnt + 1
                c_name = self.in_class[0]
                self.run_methods(p_class, method, argument, False)
                # gets variables
                inherits = copy.deepcopy(self.classes[p_class])
                self.classes[c_name]["variables"].update(inherits["variables"])
                for name in inherits["methods"].keys():
                    if name not in self.classes[c_name]["methods"].keys():
                        self.classes[c_name]["methods"][name] = inherits["methods"][name]
                self.in_class[0] = c_name
                self.in_class[1] = True
            return
            
        elif instruction.startswith("<debug>"):
            # NPP SOURCE CODE DEVELOPER DEBUGGING
            inst = instruction[8:].strip()
            if inst.startswith("var") and "_" not in inst:
                print(self.variables)
            elif inst.startswith("var_") and inst.endswith("class"):
                print(self.classes[self.in_class[0]]["variables"])
            
            
        elif instruction.startswith('load'):
            # load name[addr] = value
            # this keyword handles list loading and dictionaries aswell
            instruction = instruction[5:]
            part = instruction.split("=", 1)
            value = part[1].strip()
            parts = part[0].split("[", 1)
            
            addr = parts[1].strip().split("]")[0]
            name = parts[0].strip()
            if name not in self.variables:
                if not self.attempt:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                    print(f"\nNameError: Name {name} not a defined variable")
                self.Errors["NameError"] = True
                return None
            else:
                self.load(name, addr, value)
        
        elif instruction.startswith("break"):
            # breaks out of a loop
            if self.exec_fl <= 0:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nSyntaxError: Syntax `halt` is not inside a loop")
                self.Errors["SyntaxError"] = True
                return None
            self.breaking = False
            return
        elif instruction.startswith('continue'):
            # continues a loop back to the start
            if self.exec_fl <= 0:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nSyntaxError: Syntax `continue` is not inside a loop")
                self.Errors["SyntaxError"] = True
                return None
            self.cnt = 0
            
        elif instruction.startswith('while'):
            # like a while loop
            point = 0
            block, count = self.get_block()
            condition = instruction[6:-1] if instruction.endswith('{') else instruction[6:]
            self.exec_fl += 1
            while self.run_condition(condition):
                code = self.prep_exec(block)
                self.exec_block(code, count)
                if self.breaking:
                    self.breaking = False
                    break
                    
            self.exec_fl -= 1
            self.cnt = count
        
        elif instruction.startswith('return') and self.in_func > 0 or instruction.startswith('return') and self.in_class[1] and self.in_func > 0:
            # returns a value in a function
            self.return_val = {}
            arg = instruction[7:].strip()
            arg = self.special_split(arg, ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
            v = []
            for var in arg:
                v.append(self.eval(var, {}, self.variables))
            self.return_val = v
            self.is_return = True
            return
        
        elif instruction.startswith('global') and self.in_func:
            # makes variables global
            arg = instruction[7:].strip()
            if arg not in self.original_var:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nNameError: Name {arg} is not a variable or a defined name")
                self.Errors["NameError"] = True
                return None
            self.variables[arg] = self.original_var[arg]
            
        elif instruction.startswith('if'):
            # an if statement
            self.condition = False
            self.in_if = True
            self.if_executed = False
            condition = instruction[2:-1].strip() if instruction.endswith('{') else instruction[2:].strip()
            block, count = self.get_block()
            cond = self.run_condition(condition)
            if cond:
                self.condition = True
                self.if_executed = True
                code = self.prep_exec(block)
                self.exec_block(code, count)
                # iterates over the code till it reaches a line starting with else or a non in code block line
                count -= 1
                while True:
                    count += 1
                    if self.Instructions[count].strip().startswith('{') or self.Instructions[count].strip().endswith('{'):
                        self.in_block += 1
                    if self.Instructions[count].strip().startswith('}') and self.in_block > 0 or self.Instructions[count].strip().endswith('}') and self.in_block > 0:
                        self.in_block -= 1
                        
                    if not self.Instructions[count].strip().startswith(('{', '}', 'else')) and self.in_block == 0:
                        self.in_block, self.condition = 0, False
                        self.in_if = False
                        self.if_executed = False
                        break
                self.cnt = count - 1
                
            else:
                self.condition = False 
                # iterates over the code till it reaches a line starting with else or a non in code block line
                count -= 1
                while True:
                    count += 1
                    if self.Instructions[count].strip().startswith('{'):
                        self.in_block += 1
                    if self.Instructions[count].strip().startswith('}') and self.in_block:
                        self.in_block -= 1
                        if self.in_block == 0:
                            self.in_block = False
                    if self.Instructions[count].strip().startswith('else'):
                        break
                    if not self.Instructions[count].strip().startswith(('{', '}', 'else')) and not self.in_block:
                        self.in_block, self.condition = False, False
                        self.in_if = False
                        break
                
                self.cnt = count - 1
                
        elif instruction.startswith('else'):
            arg = instruction[4:].strip()
            arg = arg[:-1] if arg.endswith('{') else arg
            # else if statement
            if arg.startswith('if') and not self.condition:
                condition = arg[2:]
                if not self.in_if:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                    print(f"\nSyntaxError: Invalid `else if` syntax use, no if statement starting line")
                    self.Errors["SyntaxError"] = True
                    return None
                else:
                    block, count = self.get_block()
                    cond = self.run_condition(condition)
                    if cond and not self.if_executed:
                        self.condition = True
                        code = self.prep_exec(block)
                        self.exec_block(code, count)
                        self.cnt = count - 1
                    else:
                        self.condition = False
                        count -= 1
                        while True:
                            count += 1
                            if self.Instructions[count].strip().startswith('{'):
                                self.in_block += 1
                            elif self.Instructions[count].strip().startswith('}') and self.in_block:
                                self.in_block -= 1
                            elif self.Instructions[count].strip().startswith(('else', "else if")) and self.in_block == 0:
                                break
                            elif not self.Instructions[count].strip().startswith(('{', '}', 'else')) and self.in_block == 0:
                                self.in_block = 0
                                break
                        self.cnt = count - 1
            else:
                # else statement
                block, count = self.get_block()
                if not self.in_if:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                    print(f"\nSyntaxError: invalid else statement syntax use, no if and/or else if statement use before else")
                    self.Errors["SyntaxError"] = True
                    return None
                elif self.condition:
                    self.cnt = count - 1
                else:
                    self.in_if = False
                    code = self.prep_exec(block)
                    self.exec_block(code, count)
                    self.cnt = count - 1
            
        
        # for loops (for each and loops)
        elif instruction.startswith('for'):
            arg = self.special_split(instruction[4:], " in ", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"), False, 1)
            iter, arg = arg[1].strip(), arg[0].strip()
            if iter.endswith('{'): iter = iter[:-1].strip()
            if iter.startswith("range(") and iter.endswith(")"):
                iterable = list(self.ran(iter))
            else:
                iterable = self.eval(iter, {}, self.variables)
            if isinstance(iterable, str):
                iterable = list(iterable)
            block, count = self.get_block()
            if not block:
                quit()
            self.exec_fl += 1
            for cnt, val in enumerate(iterable):
                self.variables[arg] = val
                self.process_vars()
                code = self.prep_exec(block)
                self.exec_block(code, count)
                if self.breaking:
                    self.breaking = False
                    break
            self.exec_fl -= 1 
            self.cnt = count - 1
        
        elif instruction.startswith('call '):
            # calls a user defined function (also supports class methods, both inside a class and outside)
            arg = self.special_split(instruction[5:-1], "(", ("'", '"'), ("'", '"'), False, 1)
            name = arg[0]
            polymorph = False
            if any(name.startswith(aa+".") for aa in list(self.variables.keys())):
                try:
                    polymorph = True
                    name = name.split(".")
                    name = self.eval(name[0], {}, self.variables) + "." + name[1]
                except Exception:
                    name = arg[0]
            if any(name == a for a in list(self.class_callers.keys())) or any(name.startswith(a) for a in list(self.classes.keys())):
                name = name.strip().split(".")
                m_name = name[1]
                if any(name[0].startswith(a) for a in list(self.class_callers.values())):
                    if polymorph:
                        for i in list(self.class_callers.keys()):
                            if self.class_callers[i] == name[0]:
                                name = self.class_callers[i]
                    else: name = self.class_callers[name[0]]
                else: name = name[0]
                args = self.special_split(arg[1], ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                args = [self.convert_arg(arg.strip()) for arg in args]
                self.classes[name]["methods"][m_name]["end"] = self.cnt
                self.run_methods(name, m_name, args, False)
            
            elif name.startswith(self.special) and self.in_class[0] and self.in_class[1]:
                # runs class methods within the class itself
                name = name.strip().split(".", 1)
                m_name = name[1].strip()
                class_n = self.in_class[0]
                classes = self.classes[class_n]
                args = self.special_split(arg[1], ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                args = [self.convert_arg(arg.strip()) for arg in args]
                classes["methods"][m_name]["end"] = self.cnt
                self.run_methods(class_n, m_name, args, False)
                
            elif name in list(self.functions.keys()):
                a = arg[1].split(',')
                a = [self.convert_arg(ar.strip()) for ar in a]
                self.functions[name]['end'] = self.cnt
                self.run_functions(name, a, False)
            elif self.in_func:
                if self.is_priv and name in list(self.func_scope.keys()) or self.is_pub and self.func_name in list(self.func_scope.keys()):
                    a = arg[1].split(',')
                    a = [self.convert_arg(ar.strip()) for ar in a]
                    ending = self.cnt
                    if self.is_priv:
                        self.func_scope[self.og_fname]["functions"][name]['end'] = self.cnt
                    elif self.is_pub:
                        self.func_scope[self.func_name]["functions"][name]['end'] = self.cnt
                    self.run_functions(name, a, True)
                    self.cnt = ending
            if not self.in_class[1]:
                self.special = "    "
        elif instruction.startswith("public") or instruction.startswith("private"):
            type = ""
            if instruction.startswith("public"):
                instruction = instruction[7:].strip()
                type = "pub"
            elif instruction.startswith("private"):
                instruction = instruction[8:].strip()
                type = "priv"
            
            if instruction.startswith('func '):
                # user define function
                # example: `func main(arg1, arg2):`
                start = self.cnt
                arg = instruction[5:-1] if instruction.endswith('{') else instruction[5:] # ternary conditions :)
                arg = arg.rstrip("{").strip()
                arg = arg[:-1].split('(', 1) # removes the starting parenthensis and ending
                name = arg[0]
                func_arg = arg[1].split(',')
                block, count = self.get_block()
                if type == "pub":
                    self.functions[name] = {'block': block, 'args': func_arg, 'end': count, 'start': start}
                else:
                    if self.func_name not in self.func_scope.keys():
                        self.func_scope[self.func_name] = {"variables": {}, "functions": {}, "classes": {}}
                    self.func_scope[self.func_name]["functions"][name] =  {'block': block, 'args': func_arg, 'end': count, 'start': start}
                self.cnt = count - 1
        
        # error handling keywords
        elif instruction.startswith('attempt'):
            # error handling by catching errors, with throw and catch and finally
            block, count = self.get_block()
            self.attempt = True
            code = self.prep_exec(block)
            self.exec_block(code, count)
            self.cnt = count - 1
            return
        
        elif instruction.startswith('catch'): # Catching Errors
            if self.attempt:
                new_name = []
                error_name = instruction[5:-1].strip() if instruction.endswith('{') else instruction[5:]
                # strips out spaces because strip() doesnt strip out 1 letter space
                for letter in error_name:
                    if letter != " ":
                        new_name.append(letter)
                self.attempt = False # so the errors and messages out of attempt block will work
                error_name = "".join(new_name)
                block, count = self.get_block()
                if error_name in self.Errors.keys():
                    if self.Errors[name]:
                        for i in self.Errors:
                            self.Errors[i] = False
                        code = self.prep_exec(block)
                        self.exec_block(code, count)
                    self.cnt = count - 1
                elif error_name in ["any", "Exception"]:
                    if any(i for i in self.Errors.values()):
                        for i in self.Errors:
                            self.Errors[i] = False
                        code = self.prep_exec(block)
                        self.exec_block(code, count)
                    self.cnt = count - 1
                else:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                    print(f"\nNameError: Invalid Error name {error_name} not found")
                    self.Errors["NameError"] = True
                    return None
                self.attempt = False
            else:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nSyntaxError: Invalid catching syntax, no attempt block before catching")
                self.Errors["SyntaxError"] = True
                return None
        elif instruction.startswith("throw"):
            args = instruction[6:].strip().split("(", 1)
            name = args[0].strip()
            output = "output(" + args[1].strip()
            output = self.handle_output(output)
            if not name.endswith("Error"):
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nSyntaxError: Invalid name for error {name}, given must end with `Error`")
                self.Errors["SyntaxError"] = True
                return None
            try:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\n{name}: {output}")
                self.Errors[name] = True
                return None
            except Exception as e:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nSyntaxError: Invalid given output arguments for throw")
                self.Errors["SyntaxError"] = True
                return None
                
        elif instruction.startswith("import"):
            args = instruction[6:].strip().split(",")
            for lib in args:
                has_get = True if " get " in lib else False
                get_val = None
                if has_get:
                    lib = lib.split(" get ")
                    get_val = lib[1].strip()
                    lib = lib[0].strip()
                if lib in self.libraries:
                    self.library.append(lib)
                    self.library_name[lib] = lib
                    self.name_library[lib] = lib
                    # import individually if the program says so, so startup doesn't take too long
                    if lib == "time":
                        import time
                        t = time
                    elif lib == "random":
                        import random
                        r = random
                    elif lib == "math":
                        import math
                        m = math
                    elif lib == "files":
                        import json as j
                        json = j
                    elif lib == "sys":
                        import sys as s
                        sys = s
                    elif lib in self.nplibs.keys():
                        self.nplibs_acc[lib] = True # access allowed
                    else:
                        pass # some built in libraries have its own functions and methods
                    continue
                if Path(self.path / Path(lib.replace(".", "/")).with_suffix(".npp")).exists():
                    # execute .npp and get variables, functions, and methods
                    # types of imports -
                    # import file_npp <- imports full code
                    # import directory.file_npp <- imports code
                    # import file_npp get func_or_class <- imports a function or class instead of the whole code
                    types = "dir" if "." in lib else "cwd"
                    path = str(self.path)
                    if types == "dir":
                        # get directory
                        pathp = path / Path(lib.replace(".", "/")).with_suffix(".npp")
                        pathx = path / Path(lib.replace(".", "/")).with_suffix(".nxx")
                    else:
                        pathp = path / Path(lib).with_suffix(".npp")
                        pathx = path / Path(lib).with_suffix(".nxx")
                    # get name
                    split_varsp = str(pathp).rsplit("/", 1)
                    split_varsx = str(pathx).rsplit("/", 1)
                    namep = split_varsp[1]
                    namex = split_varsx[1]
                    absolute_pathp = split_varsp[0]
                    absolute_pathx = split_varsx[0]
                    if pathp.exists():
                        with open(pathp, "r") as file:
                            code = str(file.read())
                        path = pathp
                        name = namep
                        absolute_path = absolute_pathp
                    elif pathx.exists():
                        with open(pathx, "r") as file:
                            code = str(file.read())
                        name = namex
                        absolute_path = absolute_pathx
                        path = pathx
                        
                    else:
                        print("\033[31mTraceback(most_recent_call_back):\033[0m")
                        for i in self.traceback:
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                        print(f"\nModuleError: Cannot access directory `{lib}` perhaps try a different directory?")
                        self.Errors["ModuleError"] = True
                        return
                        
                    # execute code
                    npp = NPP(code, {}, absolute_path, name)
                    result = npp.execute()
                    variables = {}
                    functions = {}
                    func_scope = {}
                    classes = {}
                    name = name.removesuffix(".npp")
                    # get variables, functions, classes, and libraries
                    if has_get and get_val is not None:
                        value = get_val.split(",")
                        for get_val in value:
                            get_val = get_val.strip()
                            if get_val in npp.variables.keys():
                                variables[get_val] = npp.variables[get_val]
                            if get_val in npp.functions.keys():
                                functions[get_val] = npp.functions[get_val]
                            if get_val in npp.classes.keys():
                                classes[get_val] = npp.classes[get_val]
                    else:
                        for v in npp.variables.keys():
                            variables[name + "." + v] = npp.variables[v]
                        for f in npp.functions.keys():
                            functions[name + "." + f] = npp.functions[f]
                        for fs in npp.func_scope.keys():
                            func_scope[name + "." + f] = npp.func_scope[f]
                        for c in npp.classes.keys():
                            classes[name + "." + c] = npp.classes[c]
                    if npp.libraries:
                        self.library.extend(npp.library)
                        self.library_name.update(npp.library_name)
                        self.name_library.update(npp.name_library)
                    if npp.nplibs != {}:
                        self.nplibs.update(npp.nplibs)
                        self.nplibs_acc.update(npp.nplibs_acc)
                    self.variables.update(variables)
                    self.functions.update(functions)
                    self.classes.update(classes)
                    self.func_scope.update(func_scope)
                    self.library.append(name)
                    self.process_vars()
                else:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                    print(f"\nModuleError: Module `{lib}` not an available module")
                    self.Errors["ModuleError"] = True
                    return
                    
        elif instruction.startswith("rename"):
            # rename variables and libraries
            if " as " not in instruction:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nSyntaxError: keyword `rename` requires `as` to split both library and renamed library name, but got {instruction.strip()}")
                self.Errors["SyntaxError"] = True
                return None
                
            args = instruction[7:].strip().split(" as ")
            name = args[0].strip()
            rename = args[1].strip()
            if rename in self.forbiden_chars:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nSyntaxError: cannot convert {name} to {rename} due to containing a special character")
                self.Errors["SyntaxError"] = True
                return None
            if name in self.library_name.keys():
                self.library_name[name] = rename
                self.name_library[rename] = name
            elif name in self.variables.keys():
                self.variables[rename] = self.variables[name]
                if name != rename:
                    del self.variables[name] # so it doesn't delete the variable
        
        elif instruction.startswith("delete"):
            arg = instruction[8:].strip()
            if "[" in arg and not arg.startswith("[") and not arg.endswith("["):
                arg = arg.lsplit("[", 1)
                inst = arg[0]
            if inst in self.variables.keys():
                del self.variables[inst]
        elif instruction.startswith("sync"):
            # syncronizes variables
            # sync mode host_var with *group_varA and group_varB
            args = instruction[4:].strip()
            parts = args.split(" with ", 1)
            args = parts[0].strip().split(" ")
            mode = args[0].strip()
            host = args[1].strip()
            if host not in self.variables.keys():
                # host variables must be a real variable
                if not self.attempt:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                        print(f"\nNameError: name `{host}` is not a variable")
                        self.Errors["NameError"] = True
                    return None
                
            groups = parts[1].strip().split(" and ") # stays as a list of variable names
            # group variables can both be existing variables and non existing, if it doesn't exist, it will create a new one
            # immidietly assigning the variable with the hosts, depending what mode async is on, but immidietly as "None"
            variables = {}
            for var in groups: # variable assignments to newly defined vars
                if var not in self.variables.keys():
                    self.variables[var] = None
                variables[var] = self.variables[var]
            all_variables = variables.copy()
            all_variables.update({host: self.variables[host]})
            # sync_var dictionary
            self.sync_variables[host] = {
                "host": host,
                "past value": self.variables[host],
                "mode": mode,
                "group": groups,
                "group value": variables.copy(),
                "all": all_variables.copy(),
                "recent": None,
                "past group value": variables.copy(), # for gva only
            }
            # modes
            if mode in ["hva", "ota", "avs"]:
                # hva assigns every variables to the hosts value (hva means host value assignment)
                # ota assigns every variable to the hosts value, but only once, every variables are independent (ota means one time assignment)
                # avs assigns all variable, any variable changes will affect every group and even host variable (avs mean all variable shared)
                for var in groups:
                    variables[var] = self.variables[host]
                self.variables.update(variables)
                self.sync_variables[host]["group value"].update(variables)
                self.sync_variables[host]["past group value"].update(variables)
                self.sync_variables[host]["all"].update(variables)

            # the rest of the modes is processed through self.process_vars()
            self.process_vars()
        
        elif instruction.startswith('desync'):
            args = instruction[7:].strip()
            values = args.split(" from ")
            host = values[1].strip()
            if host not in self.sync_variables.keys():
                if not self.attempt:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                        print(f"\nNameError: name `{host}` is not a defined host variable")
                        self.Errors["NameError"] = True
                    return None
            args = values[0].strip().split(" and ")
            for vars in args:
                if vars not in self.sync_variables[host]["group"]:
                    if not self.attempt:
                        print("\033[31mTraceback(most_recent_call_back):\033[0m")
                        for i in self.traceback:
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nNameError: name `{vars}` is not defined with in `{host}` syncronization group")
                            self.Errors["NameError"] = True
                        return None
                lst = self.sync_variables[host]["group"]
                del self.sync_variables[host]["group"][lst.index(vars)]
                del self.sync_variables[host]["group value"][vars]
                del self.sync_variables[host]["all"][vars]
            
        elif instruction.startswith('class'):
            insts = instruction[5:].strip()
            inherits = False
            if insts.endswith(":"): insts = insts[:-1]
            inheritances = []
            if "(" in insts and ")" in insts:
                insts = insts[:-1].split("(", 1)
                inheritances = insts[1].split(',')
                inherits = True
                insts = insts[0]
            
            self.classes[insts] = {"methods": {}, "variables": {"<dict>": {}, "<attr>": []}, "inherits": inheritances}
            if inherits:
                for i in inheritances:
                    parent_const = {}
                    if i not in self.classes.keys():
                        continue
                    parent_const.update(copy.deepcopy(self.classes[i]))
                    if "<const>" in self.classes[i]["methods"].keys():
                        parent_const["methods"]["_" + i + "_" + "<const>"] = self.classes[i]["methods"]["<const>"].copy() # so both constructors don't get over written'
                        del parent_const["methods"]["<const>"]
                    if i:
                        self.classes[insts]["methods"].update(parent_const["methods"])
                        self.classes[insts]["variables"].update(parent_const["variables"])
                        self.classes[insts]["variables"]["<dict>"].update(parent_const["variables"])
                        self.classes[insts]["variables"]["<attr>"].update(parent_const["methods"])
                        self.classes[insts]["variables"]["<attr>"].update(parent_const["variables"])
                        
            # priv checkings example: `priv main(arg1, arg2):`
            block, count = self.get_block()
            og_inst = self.Instructions
            self.Instructions = block
            og_cnt = count
            self.cnt = 0
            while self.cnt < len(block):
                if block[self.cnt].endswith("{") and block[self.cnt].startswith("{"):
                    block[self.cnt] = block[self.cnt][:-1]
                if block[self.cnt].startswith("public func") and block[self.cnt].strip().endswith((")")) or block[self.cnt].startswith("private func") and block[self.cnt].strip().endswith((")")):
                    idks = block[self.cnt][12:-1].strip() if block[self.cnt].startswith("private") else block[self.cnt][11:-1].strip()
                    start = self.cnt
                    arg = idks.split('(') # removes the starting parenthensis and ending
                    func_name = arg[0]
                    func_arg = [a.strip() for a in arg[1].split(",")]
                    b, count = self.get_block()
                    self.classes[insts]["methods"][func_name] = {'block': b, 'args': func_arg, 'end': count, 'start': start, "type": "pub" if block[self.cnt].strip().startswith("public") else "priv"}
                    self.classes[insts]["variables"]["<attr>"].append(func_name)
                    self.cnt = count - 1
                self.cnt += 1
            self.cnt = og_cnt - 1
            self.Instructions = og_inst
            
        elif instruction.startswith(('{', '}')): pass # because it may be a peice of a code block
        
        elif instruction.startswith("open"):
            # example: open file.type as read name
            insts = instruction[5:].split(" ", 1)
            file = insts[0].strip()
            args = insts[1].strip().split("as", 1)
            types = args[0].strip()
            name = args[1].strip()
            modes = ["read", "write", "append", "binary", "create", "text"]
            convert = {
                "read": "r",
                "write": "w",
                "append": "a",
                "create": "x",
                "binary": "b",
                "text": "t"
            }
            if types not in modes:
                if not self.attempt:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                        print(f"\nTypeError: no such file type named `{types}`")
                        self.Errors["TypeError"] = True
                    return None
            if any(ch in name for ch in self.forbiden_chars):
                if not self.attempt:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                        print(f"\nValueError: name `{name}` contains a special character the function couldn't support")
                        self.Errors["ValueError"] = True
                    return None
            types = convert[types]
            
            file = self.eval(file, {}, self.variables)
            if not file.startswith("$/"): # starting
                file = self.path + "/" + file
            else:
                file = file[1:].strip()
            self.variables[name] = open(file, types)
            self.constants[name] = [True, open(file, types)]
        
        # LAYER 2 OF PARSING
        elif '=' in instruction:
            self.assign_variable(instruction)
            self.process_vars()
        
            
        elif '.' in instruction:
            func = self.special_split(instruction, ".", ('"', "'"), ('"', "'"))
            name = func[0]
            cnt = 1
            while cnt < len(func):
                if func[cnt].startswith('push(') and func[cnt].endswith(')'):
                    args = func[cnt][5:-1]
                    if not isinstance(self.variables[name], list):
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nValueError: can't push variable as it is not a list")
                        self.Errors["ValueError"] = True
                    else:
                        if args:
                            try:
                                self.variables[name].append(self.eval(args, {}, self.variables))
                            except Exception as e:
                                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                                for i in self.traceback:
                                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                print(f"\nTypeError: can't evaluate expression {args}")
                                self.Errors["TypeError"] = True
                                return None
                elif func[cnt].startswith('freeze(') and func[cnt].endswith(')'):
                    if not isinstance(self.variables[name], set):
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nTypeError: given variable or value type is not a set")
                        self.Errors["TypeError"] = True
                        return None
                    self.variables[name] = frozenset(self.variables[name])
                elif func[cnt].startswith('set(') and func[cnt].endswith(')'):
                    if not isinstance(self.variables[name], set):
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            
                            print(f"\nValueError: the data type given of the variable {name} -> `{self.variables[name]}` is not a set")
                        self.Errors["ValueError"] = True
                        return None
                    self.variables[name] = set(self.variables[name])
                elif func[cnt].startswith("close(") and func[cnt].endswith(")"):
                    self.variables[name].close()
                    
                elif func[cnt].startswith("write(") and func[cnt].endswith(")"):
                    arg = func[cnt][6:-1].strip()
                    value = self.eval(arg, {}, self.variables)
                    self.variables[name].write(value)
                elif func[cnt].startswith("extend(") and func[cnt].endswith(")"):
                    arg = func[cnt][7:-1].strip()
                    value = self.eval(arg, {}, self.variables)
                    self.variables[name].extend(value)
                elif func[cnt].startswith("update(") and func[cnt].endswith(")"):
                    arg = func[cnt][7:-1].strip()
                    value = self.eval(arg, {}, self.variables)
                    self.variables[name].update(value)
                cnt += 1
            if self.libraries:
                if any(instruction.strip().startswith(self.library_name[l] + ".") and l in self.library for l in self.nplibs.keys()):
                    struct = instruction.split(".", 1)
                    key = self.name_library[struct[0]]
                    module = self.nplibs[key]
                    lib = module(**self.__dict__)
                    result = lib.process(instruction, variant="ol")
                    if result == [] or result is None:
                        return
                    if len(result) > 0:
                        self.variables = result[0]
                    if len(result) > 1:
                        self.cnt = result[1]
                    return
                lib = libraries(**self.__dict__)
                result = lib.process(instruction, t, m, r, json, sys, variant="ol")
                if result == [] or result is None:
                    return
                
                if len(result) > 0:
                    if not result[0].startswith("$<<"):
                        self.variables = result[0]
                    else:
                        if result[0] == "$<<SELF EVAL>>" and not self.eval_deb:
                            self.eval_deb = True
                        elif result[0] == "$<<SELF EVAL>>" and self.eval_debs:
                            self.eval_deb = False
                        elif result[0] == "$<<DEBUGGED>>" and not self.debug:
                            self.debug = True
                        elif result[0] == "$<<DEBUGGED>>" and self.debug:
                            self.debug = False
                        elif result[0] == "$<<ADV_DEBUGGED>>" and not self.adv_debug:
                            self.debug = True
                        elif result[0] == "$<<ADV_DEBUGGED>>" and self.adv_debug:
                            self.debug = False
                if len(result) > 1:
                    self.cnt = result[1]
                # libraries already access whatever is inside npp, result is a dict
                
        else:
            print("\033[31mTraceback(most_recent_call_back):\033[0m")
            for i in self.traceback:
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
            print(f"\nSyntaxError: Instruction/syntax format `{instruction}` not parsed")
            self.Errors["SyntaxError"] = True
            return None
            
    def assign_variable(self, instruction, run_method=False):
        """
        Main Level 2 of parsing
        where variable assignments are handled
        but also can be the 4th layer of parsing by self.eval()
        """
        stuff = instruction.split('=', 1)
        libs = False
        left = stuff[0].strip()
        right = stuff[1].strip()
        ismethod = False
        # Handle values of string literals, so method doesnt get involved in strings
        ismeth = self.special_find(right, ".", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
        pattern = r'(?<!\w)[+-]?(?:\d+\.\d+|\d+\.|\.\d+)(?!\w)'
        if ismeth and not right.startswith(self.special) and bool(re.search(pattern, right)):
            ismethod = False
        else:
            ismethod = True
            
        if not right.startswith(self.special):
            if not right.startswith("call") and not bool(re.search(pattern, right)):
                main = self.special_split(right, ".", ("'", '"', "("), ("'", '"', ")"))
            else: main = right.strip()
        else: main = right.strip()
        if isinstance(main, list):
            main = main[0].strip()
            if main.startswith(self.special) or main == self.special:
                main += "." + self.special
        else: main = main.strip()
        # for imports
        if main in self.library:
            main = right
        # handles multiple variable names (like val1, val2 = stuff)
        l = self.special_split(left, ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
        # if single name
        if len(l) == 1:
            left = l[0]
        else:
            left = l # full list instead
        
        if left not in self.variables.keys():
            self.constants[left] = [True, None]
        # runs self.eval if contains arithmetic
        istrue = [
            self.special_find(main, "+", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}")),
            self.special_find(main, "-", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}")),
            self.special_find(main, "*", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}")),
            self.special_find(main, "/", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}")),
            self.special_find(main, "**", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}")),
            self.special_find(main, "//", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}")),
        ]
        pre_run = False
        if any(istrue) and not self.evals:
            self.variables[left] = self.eval(main, {}, self.variables)
            pre_run = True
        def built_in_functions(left, main, right, method):
            global m, r, t, json, sys
            libs = False
            try:
                if main.startswith('num(') and main.endswith(')'):
                    self.handle_num_function(left, main)
                    return
                elif main in list(self.variables.keys()):
                    self.variables[left] = self.variables[main]
                    return
                    
                elif main.startswith('input(') and main.endswith(')'):
                    output = main.split('(', 1)
                    content = str(output[1][:-1])
                    if content.startswith('"') and content.endswith('"') or content.endswith("'") and content.startswith("'"):
                        out = content[1:-1]
                    else:
                        try:
                            out = str(self.eval(content, {}, self.variables))
                        except Exception:
                            out = content
                    value = input(out)
                    self.variables[left] = value
                    return
                    
                elif main.startswith('length(') and main.endswith(')'):
                    arg = main[7:-1]
                    try:
                        value = self.eval(arg.strip(), {}, self.variables)
                    except Exception as e:
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nTypeError: {e}")
                        self.Errors["TypeError"] = True
                        return None
                    if value:
                        self.variables[left] = len(value)
                    return
                elif main.startswith('range(') and main.endswith(')'):
                    self.variables[left] = self.ran(main)
                    return    
                elif main.startswith('format(') and main.endswith(")"):
                    content = main[7:-1].strip()
                    if content.startswith('"') and content.endswith('"') or content.startswith("'") and content.endswith("'"):
                        content = content[1:-1]
                    # Extract expressions inside the curly braces and evaluate
                    new_content = ""
                    parts = re.split(r'({[^}]*})', content)  # Split by expressions in curly braces
                    for part in parts:
                        if part.startswith("{") and part.endswith("}"):
                            expression = part[1:-1]  # Remove curly braces
                            evaluated = self.eval(expression, {}, self.variables)
                            new_content += str(evaluated)  # Append the evaluated result
                        else:
                            new_content += part  # Append the literal text
                    self.variables[left] = new_content
                    return
                elif main.startswith('eval(') and main.endswith(')'):
                    arg = self.special_split(main[5:-1], ",", ("'", '"', "(", "{", "["), ('"', "'", ")", "]", "}"))
                    try:
                        if len(arg) > 1:
                            a1 = arg[1].strip()
                            globald = self.eval(a1, {}, self.variables)
                            if len(arg) > 2:
                                a2 = arg[2].strip()
                                locald= self.eval(a2, {}, self.variables)
                                if len(arg) > 3:
                                    arb = self.eval(arg[3].strip(), {}, self.variables)
                                else: 
                                    arb = False
                            else:
                                locald = {}
                        else:
                            globald = {}
                            locald = {}
                        argument = self.eval(arg[0].strip(), {}, self.variables, arb)
                        locald.update(self.variables)
                        self.variables[left] = self.eval(argument, globald, locald, arb)
                        return
                    except Exception as e:
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                print(f"\nValueError: Value '{arg[1]}' cannot be evaluated. {e}")
                                print(self.classes[self.in_class[0]]["variables"])  
                                self.Errors["ValueError"] = True
                            return None
                
                elif main.startswith('call'):
                    arg = main[5:-1].split('(', 1)
                    
                    name = arg[0]
                    polymorph = False
                    if any(name.startswith(aa+".") for aa in list(self.variables.keys())):
                        
                        try:
                            polymorph = True
                            name = name.rsplit(".")
                            name = self.eval(name[0], {}, self.variables) + "." + name[1]
                        except Exception:
                            name = arg[0]
                    if any(name == a for a in list(self.class_callers.keys())) or name.startswith(self.special) and self.in_class[0] or any(name.startswith(a) for a in list(self.classes.keys())):
                        name = name.strip().rsplit(".", 1)
                        m_name = name[1]
                        self.traceback[m_name] = self.og_c
                        if any(name[0].startswith(a) for a in list(self.class_callers.values())):
                            if polymorph:
                                for i in list(self.class_callers.keys()):
                                    if self.class_callers[i] == name[0]:
                                        name = self.class_callers[i]
                            else: name = self.class_callers[name[0]]
                        else: name = self.in_class[0]
                        args = arg[1].split(',')
                        args = [self.convert_arg(arg.strip()) for arg in args]
                        self.classes[name]["methods"][m_name]["end"] = self.cnt 
                        t = False if self.classes[name]["methods"][m_name]["type"] == "pub" else True
                        self.run_methods(name, m_name, args, t)
                        if self.is_return:
                            if isinstance(left, str):
                                left = [left]
                            for v, n in zip(self.return_val, left):
                                self.variables[n] = v
                            self.is_return = False
                    elif name in list(self.functions.keys()):
                        a = arg[1].split(',')
                        a = [self.convert_arg(ar.strip()) for ar in a]
                        self.functions[name]['end'] = self.cnt
                        self.traceback[name] = self.og_c
                        self.run_functions(name, a, False)
                        if self.is_return:
                            if isinstance(left, str):
                                left = [left]
                            for v, n in zip(self.return_val, left):
                                self.variables[n] = v
                            self.is_return = False
                    elif self.in_func:
                        if self.is_priv and name in list(self.func_scope.keys()) or self.is_pub and self.func_name in list(self.func_scope.keys()):
                            a = arg[1].split(',')
                            a = [self.convert_arg(ar.strip()) for ar in a]
                            ending = self.cnt
                            if self.is_priv:
                                self.func_scope[self.og_fname]["functions"][name]['end'] = self.cnt
                            elif self.is_pub:
                                self.func_scope[self.func_name]["functions"][name]['end'] = self.cnt
                            self.traceback[name] = self.og_c
                            self.run_functions(name, a, True)
                            if self.is_return:
                                if isinstance(left, str):
                                    left = [left]
                                for v, n in zip(self.return_val, left):
                                    self.variables[n] = v
                                self.is_return = False
                            self.cnt = ending
                    if not self.in_class[1]:
                        self.special = "    "
                    return
                elif main.startswith('sort(') and main.endswith(')'):
                    arg = main[5:-1].split(',')
                    reverse = self.eval(arg[1].strip(), {}, self.variables) if len(arg) == 2 else False
                    if not isinstance(reverse, bool):
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nTypeError: second given argument to sort() is not a boolean value")
                        self.Errors["TypeError"] = True
                        return
                    name = self.eval(arg[0], {}, self.variables)
                    # sort(list, reverse=False) reverse being boolean, and list as variable name that is a list
                    if len(arg) > 2:
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nTypeError: sort() expected 2 arguments, but got {len(arg)}")
                        self.Errors["TypeError"] = True
                        return
                    elif isinstance(arg, list):
                        if isinstance(name, list) and len(arg) == 2 or reverse or not reverse:
                            if not reverse:
                                self.variables[left] = sorted(name)
                            elif reverse:
                                sort_val = sorted(name)
                                self.variables[left] = list(reversed(sort_val))
                            return
                        if not isinstance(name, list):
                            if not self.attempt:
                                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                                for i in self.traceback:
                                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                print(f"\nTypeError: sort() 1st given argument is not a list")
                            self.Errors["TypeError"] = True
                            return
                    return
                elif main.startswith("mean(") and main.endswith(")"):
                    arg = self.eval(main[5:-1].strip(), {}, self.variables)
                    if not isinstance(arg, list):
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nValueError: given value is not a list")
                        self.Errors["ValueError"] = True
                        return None
                    val = sum(arg)
                    self.variables[left] = val / len(arg)
                    return
                elif main.startswith("median(") and main.endswith(")"):
                    arg = self.eval(main[7:-1].strip(), {}, self.variables)
                    if not isinstance(arg, list):
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nValueError: given value is not a list")
                        self.Errors["ValueError"] = True
                        return None
                    lists = sorted(arg)
                    length = len(lists) / 2
                    if not str(length).endswith(".5"):
                        mid1 = int(length) - 1
                        mid2 = mid1 + 1
                        stuffs = lists[mid1] + lists[mid2]
                        self.variables[left] = stuffs / 2
                    else:
                        mid = int(length)
                        self.variables[left] = float(lists[mid])
                    return
                elif main.startswith("mode(") and main.endswith(")"):
                    arg = self.eval(main[5:-1].strip(), {}, self.variables)
                    if not isinstance(arg, list):
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nValueError: given value is not a list")
                        self.Errors["ValueError"] = True
                        return None
                    counts = {}
                    for i in arg:
                        counts[str(i)] = 0
                    for i in arg:
                        counts[str(i)] += 1
                    highest = 0
                    for i in counts:
                        if int(counts[str(i)]) >= int(highest):
                            highest = i
                            
                    self.variables[left] = highest
                    return
                elif main.startswith("sum(") and main.endswith(")"):
                    arg = self.eval(main[4:-1].strip(), {}, self.variables)
                    if not isinstance(arg, list):
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nValueError: given value {arg} is not a list")
                        self.Errors["ValueError"] = True
                        return None
                    self.variables[left] = sum(arg)
                    return
                elif main.startswith("max(") and main.endswith(")"):
                    arg = main[4:-1].strip().split(",", 1)
                    value = self.eval(arg[0], {}, self.variables)
                    if len(arg) == 2:
                        self.variables[left] = max(value, default=arg[1])
                    else:
                        self.variables[left] = max(value)
                    return
                elif main.startswith("min(") and main.endswith(")"):
                    arg = main[4:-1].strip().split(",", 1)
                    value = self.eval(arg[0], {}, self.variables)
                    if len(arg) == 2:
                        self.variables[left] = min(value, default=arg[1])
                    else:
                        self.variables[left] = min(value)
                    return
                
                elif main.startswith("reverse(") and main.endswith(")"):
                    arg = main[8:-1].strip()
                    value = self.eval(arg, {}, self.variables)
                    self.variables[left] = value[::-1]
                    return
                
                elif main.startswith("type(") and main.endswith(")"):
                    arg = main[5:-1].strip().split(",", 1)
                    value = self.eval(arg[0].strip(), {}, self.variables)
                    if len(arg) == 2:
                        mode = arg[1].strip()
                    else:
                        self.variables[left] = type(value)
                        return
                    self.variables[left] = self.types(value, mode)
                    return
                elif main.startswith("zip(") and main.endswith(")"):
                    arg = self.special_split(main[4:-1].strip(), ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                    new_list = []
                    for value in arg:
                        new_list.append(self.eval(value.strip(), {}, self.variables))
                    self.variables[left] = list(zip(*new_list))
                    return
                elif main.startswith("dict(") and main.endswith(")"):
                    arg = self.special_split(main[5:-1].strip(), ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                    if len(arg) < 2:
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                print(f"\nValueError: expected arguments for dict() are `2` but got `{len(arg)}`")
                                self.Errors["ValueError"] = True
                            return None
                    arg[0] = self.eval(arg[0], {}, self.variables)
                    arg[1] = self.eval(arg[1], {}, self.variables)
                    if len(arg[0]) != len(arg[1]):
                        if not self.attempt:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                print(f"\nValueError: both arguments must be at the same length")
                                self.Errors["ValueError"] = True
                            return None
                    dicts = {}
                    for v in range(len(arg[1])):
                        dicts[arg[0][v]] = arg[1][v]
                    self.variables[left] = dicts
                    return
                elif main in self.functions.keys():
                    arg = self.functions[main.strip()]
                    # just copies it as variable left name
                    self.functions[left] = arg
                    self.variables[left] = main
                    return
                # handles classes
                elif main.startswith(tuple(self.classes.keys())):
                    name = None
                    for i in self.classes.keys():
                        if i in main:
                            name = i
                    if "(" in main and ")" in main and "<const>" in list(self.classes[name]["methods"].keys()):
                        args = main[:-1].split("(", 1)
                        name = args[0]
                        
                        m_name = "<const>"
                        args = args[1].split(',')
                        args = [self.convert_arg(arg.strip()) for arg in args]
                        self.classes[name]["methods"]["<const>"]["end"] = self.cnt + 1
                        self.run_methods(name, m_name, args, False)
                    self.class_callers[left] = name
                    self.variables[left] = name
                    ogl = left
                    left = "__" + left + "__"
                    self.cnt -= 1
                    self.variables[left] = ogl
                    return
                # handles list, tuples, dictionaries
                elif main.startswith(("[", "(", "{")):
                    # this code handles item values where not only it supports normally loading items, but also items that stretches with the end further down on the code
                    # normal assignment
                    if main.startswith("[") and main.endswith("]") or main.startswith("(") and main.endswith(")") or main.startswith("{") and main.endswith("}"):
                        self.variables[left] = self.eval(main, {}, self.variables)
                        return
                    else:
                        # handles complex long assignments (like multi lined)
                        args = main.strip()
                        structure, count = self.get_items(args)
                        self.cnt = count - 1
                        item_now = ""
                        for i in structure:
                            item_now += str(i)
                        self.variables[left] = self.eval(item_now, {}, self.variables)
                    return
                elif self.library and "." in right:
                    if any(instruction.strip().startswith(self.library_name[l] + ".") and l in self.library for l in self.nplibs.keys()):
                        struct = instruction.split(".", 1)
                        key = self.name_library[struct[0]]
                        module = self.nplibs[key]
                        lib = module(**self.__dict__)
                        result = lib.process(instruction, variant="ol")
                        if result == [] or result is None:
                            return
                        if len(result) >= 1:
                            self.variables = result[0]
                            return
                    lib = libraries(**self.__dict__)
                    result = lib.process((left, right), t, m, r, json, sys, variant="av")
                    if result == [] or result is None:
                        pass
                    if len(result) >= 1:
                        self.variables = result[0]
                        return
                if not libs:
                    """
                    3rd Layer of parsing
                    """
                    main = main.replace('++', '<<').replace('--', '>>')
                    self.variables[left] = self.eval(main, {}, self.variables)
            except Exception as e:
                if isinstance(e, ZeroDivisionError):
                    if not self.attempt:
                        print("\033[31mTraceback(most_recent_call_back):\033[0m")
                        for i in self.traceback:
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                        print(f"\nZeroDivisionError: can't divide by 0...")
                    self.Errors["ZeroDivisionError"] = True
                    return None
                if isinstance(e, MemoryError):
                    if not self.attempt:
                        print("\033[31mTraceback(most_recent_call_back):\033[0m")
                        for i in self.traceback:
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                        print(f"\nMemoryError: why would you do this")
                    self.Errors["MemoryError"] = True
                    return
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nSyntaxError: Invalid given syntax {main}, {e}")
                self.Errors["SyntaxError"] = True
                return None
        if not run_method and not pre_run:
            built_in_functions(left, main, right, ismethod)
        else:
            if ismethod:
                self.methods(left, right)
        # class vars
        if any(left in self.classes[vs]["variables"].keys() for vs in self.classes.keys()) and self.in_class[1]:
            self.classes[self.in_class[0]]["variables"][left] = self.variables[left]

        if self.constants[left][0] and self.constants[left][1] == None and left in self.variables.keys():
            
            self.constants[left][1] = self.variables[left]
        if ismethod:
            self.methods(left, right) # next is methods
        return
    def methods(self, left, right):
        """
        3rd layer of parsing
        this handles built in methods and assigns them to the variable
        this also handles multiple built in methods instead of doing it one by one
        """
        try:
            if '.' in right:
                var_func = self.special_split(right, ".", ("'", '"'), ("'", '"'))
                if var_func[0] not in self.variables:
                    name = left
                else:
                    name = var_func[0]
                cnt = 1
                while cnt < len(var_func):
                    if var_func[cnt].startswith('cap(') and var_func[cnt].endswith(')') :
                        func = var_func[cnt][4:-1]
                        arg_er = list(func.split(',')) # list() because if no comma, it wouldnt be a list
                        if func != '':
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nSyntaxError: cap() method doesn't support any arguments")
                            self.Errors["SyntaxError"] = True
                            break
                        self.variables[left] = self.variables[name].upper() if isinstance(self.variables[name], str) else None
                        if self.variables[left] is None:
                            if not self.attempt:
                                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                                for i in self.traceback:
                                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                print(f"\nTypeError: Given variable is not a string")
                            self.Errors["TypeError"] = True
                            return
                    if var_func[cnt].startswith('low(') and var_func[cnt].endswith(')') :
                        func = var_func[cnt][4:-1]
                        arg_er = list(func.split(','))
                        if func != '':
                            if not self.attempt:
                                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                                for i in self.traceback:
                                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                print(f"\nTypeError: low() method doesn't expext an argument, but {len(arg)} is given")
                            self.Errors["TypeError"] = True
                            return
                        self.variables[left] = self.variables[name].lower() if isinstance(self.variables[name], str) else None
                        if self.variables[left] is None:
                            if not self.attempt:
                                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                                for i in self.traceback:
                                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                print(f"\nTypeError: given variable or value is not a string")
                            self.Errors["TypeError"] = True
                            return
                    elif var_func[cnt].startswith('as(') and var_func[cnt].endswith(')'):
                        args = var_func[cnt].strip(')')[3:-1]
                        if name in self.variables:
                            try:
                                if args in self.variables:
                                    arg = self.variables[args]
                                    if arg not in ["int", "interger", "str", "string", "flt", "float", "list", "tuple"]:
                                        pass
                                    else:
                                        args = arg
                                if args in ['int', 'interger']:
                                    self.variables[left] = int(self.variables[name])
                                    return
                                elif args in ['str', 'string']:
                                    self.variables[left] = str(self.variables[name])
                                    return
                                elif args in ['flt', 'float']:
                                    self.variables[left] = float(self.variables[name])
                                    return
                                elif 'bool' in args:
                                    self.variables[left] = bool(self.variables[name])
                                    return
                                elif "list" in args:
                                    self.variables[left] = list(self.variables[name])
                                    return
                                elif "tuple" in args:
                                    self.variables[left] = tuple(self.variables[name])
                                    return
                                else:
                                    if not self.attempt:
                                        print("\033[31mTraceback(most_recent_call_back):\033[0m")
                                        for i in self.traceback:
                                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                        print(f"\nTypeError: as() method expected a string argument, not {type(args)}")
                                    self.Errors["Error"] = True
                                    return

                            except ValueError:
                                if not self.attempt:
                                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                                    for i in self.traceback:
                                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                    print(f"\nValueError: {self.variables[name]} can't be converted into {args}")
                                self.Errors["ValueError"] = True
                                return
                    elif var_func[cnt].startswith('rem(') and var_func[cnt].endswith(')'):
                        argu = var_func[cnt][4:-1]
                        if argu != "":
                            func = self.eval(argu, {}, self.variables)
                        else:
                            func = argu
                        self.variables[left] = self.variables[name].replace(func, "")
                        return
                    elif var_func[cnt].startswith("strip(") and var_func[cnt].endswith(")"):
                        argu = var_func[cnt][6:-1]
                        self.variables[left] = self.variables[name].strip(argu)
                        return
                    elif var_func[cnt].startswith("split(") and var_func[cnt].endswith(")"):
                        argu = self.special_split(var_func[cnt][6:-1], ",", ("(", "'", '"', "[", "{"), (")", "'", '"', "]", "}"))
                        group = self.eval(argu[0].strip(), {}, self.variables)
                        if len(argu) > 1:
                            limit = self.eval(argu[1].strip(), {}, self.variables)
                            
                            self.variables[left] = self.variables[name].split(group, limit)
                        else:
                            self.variables[left] = self.variables[name].split(group)
                        return
                        
                    # strwith() method as startswith() and endwith() as endswith()
                    elif var_func[cnt].startswith("hasprefix(") and var_func[cnt].endswith(')'):
                        arg = var_func[cnt][10:-1].strip()
                        arg = arg[1:-1] if arg.startswith('"') and arg.endswith('"') or arg.startswith("'") and arg.endswith("'") else arg
                        if self.variables[name].startswith(arg):
                            self.variables[left] = True
                        else:
                            self.variables[left] = False
                            
                    elif var_func[cnt].startswith("hassuffix(") and var_func[cnt].endswith(")"):
                        arg = var_func[cnt][10:-1].strip()
                        arg = arg[1:-1] if arg.startswith('"') and arg.endswith('"') or arg.startswith("'") and arg.endswith("'") else arg
                        if self.variables[name].endswith(arg):
                            self.variables[left] = True
                        else:
                            self.variables[left] = False
                            
                    elif var_func[cnt].startswith("replace(") and var_func[cnt].endswith(")"):
                        arg = self.special_split(var_func[cnt][8:-1].strip(), ",", ("'", '"'), ("'", '"'))
                        arg1 = self.eval(arg[0], {}, self.variables)
                        arg2 = self.eval(arg[1], {}, self.variables)
                        if arg1.startswith("(") and arg1.endswith(")"):
                            arg1 = tuple(arg1)
                        self.variables[left] = self.variables[name].replace(arg1, arg2)
                    
                    elif var_func[cnt].startswith("slice(") and var_func[cnt].endswith(")"):
                        arg = var_func[cnt].strip()[6:-1]
                        arg = self.special_split(arg, ",", ("(", "'", '"'), (")", "'", '"'))
                        if not isinstance(arg, list):
                            arg = [arg]
                        for i, v in enumerate(arg):
                            arg[i] = self.eval(v, {}, self.variables)
                        if len(arg) < 3:
                            if len(arg) < 2:
                                arg.append(len(self.variables[name]))
                            arg.append(1)
                        if arg[0] == ":" and arg[1] != ":":
                            value = self.variables[::int(arg[1])]
                        elif arg[0] != ":" and arg[1] == ":":
                            value = self.variables[name][int(arg[0])::int(arg[2])]
                        else:
                            value = self.variables[name][int(arg[0]):int(arg[1]):int(arg[2])]
                        self.variables[left] = value
                        
                    elif var_func[cnt].startswith("pop(") and var_func[cnt].endswith(')'):
                        arg = var_func[cnt][4:-1]
                        try:
                            arg = self.eval(arg, {}, self.variables) if arg else arg
                        except Exception as e:
                            print("\033[31mTraceback(most_recent_call_back):\033[0m")
                            for i in self.traceback:
                                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                            print(f"\nSyntaxError: invalid expression of pop() method !-> {args}")
                            self.Errors["SyntaxError"] = True
                            return
                        if not arg:
                            self.variables[left] = self.variables[name].pop()
                        elif isinstance(arg, bool) and isinstance(self.variables[name], list):
                            if arg:
                                # pops like an FIFO
                                self.variables[left] = self.variables[name].pop(0)
                            else:
                                # pops like the LIFO
                                self.variables[left] = self.variables[name].pop()
                        else:
                            if isinstance(arg, int) and isinstance(self.variables[name], list):
                                if arg <= len(self.variables[name]):
                                    self.variables[left] = self.variables[name].pop(arg)
                                else:
                                    if not self.attempt:
                                        print("\033[31mTraceback(most_recent_call_back):\033[0m")
                                        for i in self.traceback:
                                            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                        print(f"\nIndexError: pop() method index is out of range")
                                    self.Errors["IndexError"] = True
                                    return
                            else:
                                if not self.attempt:
                                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                                    for i in self.traceback:
                                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                                    print(f"\nValueError: {name} is not a list")
                                self.Errors["ValueError"] = True
                                return
                    elif var_func[cnt].startswith("push(") and var_func[cnt].endswith(")"):
                        arg = var_func[cnt][5:-1].strip()
                        value = self.eval(arg, {}, self.variables) # value to push
                        self.variables[name].append(value)
                        self.variables[left] = self.variables[name]
                        
                    elif var_func[cnt].startswith("read(") and var_func[cnt].endswith(")"):
                        arg = var_func[cnt][5:-1]
                        self.variables[left] = self.variables[name].read()
                    elif var_func[cnt].startswith("keys(") and var_func[cnt].endswith(")"):
                        arg = var_func[cnt][5:-1]
                        self.variables[left] = self.variables[name].keys()
                    elif var_func[cnt].startswith("items(") and var_func[cnt].endswith(")"):
                        arg = var_func[cnt][6:-1]
                        self.variables[left] = self.variables[name].items()
                    elif var_func[cnt].startswith("values(") and var_func[cnt].endswith(")"):
                        arg = var_func[cnt][7:-1]
                        self.variables[left] = self.variables[name].values()
                    elif var_func[cnt].startswith("const(") and var_func[cnt].endswith(")"):
                        arg = var_func[cnt][6:-1].strip()
                        self.constants[left] = [True, self.variables[name]]
                        self.variables[left] = self.variables[name]
                    elif var_func[cnt].startswith("unconst(") and var_func[cnt].endswith(")"):
                        arg = var_func[cnt][8:-1].strip()
                        self.constants[left] = [False, self.variables[name]]
                        self.variables[left] = self.variables[name]
                    cnt += 1
                self.process_vars()
            else:
                return
        except Exception as e:
            print(e)
            print("\033[31mTraceback(most_recent_call_back):\033[0m")
            for i in self.traceback:
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
            print(f"\nSyntaxError: invalid method: {var_func[cnt]}")
            self.Errors["SyntaxError"] = True
            return
    
    def ran(self, main):
        # for the built in range(start, end, set)
        # the range() function, i just ask myself why did i did this?
        arg = main[6:-1].split(',')
        start = self.eval(arg[0], {}, self.variables)
        end = self.eval(arg[1], {}, self.variables) if len(arg) >= 2 else None
        set = self.eval(arg[2], {}, self.variables) if len(arg) == 3 else 1
        if not isinstance(start, int):
            if not self.attempt:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nTypeError: range() 1st argument is not a interger")
            self.Errors["TypeError"] = True
            return None
        elif not isinstance(end, int) and end is not None:
            if not self.attempt:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nTypeError: range() 2nd argument `{end}` is not an interger")
            self.Errors["TypeError"] = True
            return None
        elif not isinstance(set, int):
            if not self.attempt:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nTypeError: range() 3rd argument `set` is not an interger")
            self.Errors["TypeError"] = True
            return None
        if end is None:
            list_ran = range(0, start, set)
        else:
            list_ran = range(start, end, set)
        return list_ran
        
    def handle_num_function(self, left, right):
        """Prepares and process the arguments of num()"""
        try:
            func_params = right[4:-1].split(',')
            if len(func_params) == 2:
                value = self.eval(func_params[0].strip(), {}, self.variables)
                numsys = func_params[1].strip().strip('"')
                self.variables[left] = self.num(value, numsys)
            else:
                print("\033[31mTraceback(most_recent_call_back):\033[0m")
                for i in self.traceback:
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                print(f"\nSyntaxError: invalid parimeter for num function")
                self.Errors["SyntaxError"] = True
                return
        except Exception as e:
            print("\033[31mTraceback(most_recent_call_back):\033[0m")
            for i in self.traceback:
                print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
            print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
            print(f"\nSyntaxError: {e}")
            self.Errors["SyntaxError"] = True
            return
    
    def handle_output(self, instruction):
        """handles for the output() function
        this not only handles printing variables and values, but also built in functions, expressions,
        user defined functions, class methods (in and out of the class scope), and even formsted strings
        """
        content = instruction[7:-1].strip() if instruction.startswith("output(") else instruction # Extract content within output(...)
        if not content:
            return ""
        # Handle output of string literals, variables, and expressions    
        if instruction.startswith('call '):
            # calls a user defined function (also supports class methods, both inside a class and outside)
            arg = self.special_split(instruction[5:-1], "(", ("'", '"'), ("'", '"'), False, 1)
            name = arg[0]
            polymorph = False
            if any(name.startswith(aa+".") for aa in list(self.variables.keys())):
                try:
                    polymorph = True
                    name = name.split(".")
                    name = self.eval(name[0], {}, self.variables) + "." + name[1]
                except Exception:
                    name = arg[0]
            if any(name == a for a in list(self.class_callers.keys())) or any(name.startswith(a) for a in list(self.classes.keys())):
                name = name.strip().split(".")
                m_name = name[1]
                if any(name[0].startswith(a) for a in list(self.class_callers.values())):
                    if polymorph:
                        for i in list(self.class_callers.keys()):
                            if self.class_callers[i] == name[0]:
                                name = self.class_callers[i]
                    else: name = self.class_callers[name[0]]
                else: name = name[0]
                args = self.special_split(arg[1], ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                args = [self.convert_arg(arg.strip()) for arg in args]
                self.classes[name]["methods"][m_name]["end"] = self.cnt
                v = self.run_methods(name, m_name, args, False)
            
            elif name.startswith(self.special) and self.in_class[0] and self.in_class[1]:
                # runs class methods within the class itself
                name = name.strip().split(".", 1)
                m_name = name[1].strip()
                class_n = self.in_class[0]
                classes = self.classes[class_n]
                args = self.special_split(arg[1], ",", ('"', "'", "(", "[", "{"), ('"', "'", ")", "]", "}"))
                args = [self.convert_arg(arg.strip()) for arg in args]
                classes["methods"][m_name]["end"] = self.cnt
                v = self.run_methods(class_n, m_name, args, False)
                
            elif name in list(self.functions.keys()):
                a = arg[1].split(',')
                a = [self.convert_arg(ar.strip()) for ar in a]
                self.functions[name]['end'] = self.cnt
                v = self.run_functions(name, a, False)
            elif self.in_func:
                if self.is_priv and name in list(self.func_scope.keys()) or self.is_pub and self.func_name in list(self.func_scope.keys()):
                    a = arg[1].split(',')
                    a = [self.convert_arg(ar.strip()) for ar in a]
                    ending = self.cnt
                    if self.is_priv:
                        self.func_scope[self.og_fname]["functions"][name]['end'] = self.cnt
                    elif self.is_pub:
                        self.func_scope[self.func_name]["functions"][name]['end'] = self.cnt
                    v = self.run_functions(name, a, True)
                    self.cnt = ending
            if not self.in_class[1]:
                self.special = "    "
            return v
        elif content.startswith('"') and content.endswith('"') or content.endswith("'") and content.startswith("'"):
            return content[1:-1]  # Output string literal
        elif self.in_class[1] and content in self.classes[self.in_class[0]]["variables"].keys():
            return self.classes[self.in_class[0]]["variables"][content]
        elif content in self.variables.keys():
            return self.variables[content]  # Output variable value
        elif content.startswith('f(') and content.endswith(')'):  # Format handling
            content = content.strip('f(').strip(')')
            if content.startswith('"') and content.endswith('"') or content.startswith("'") and content.endswith("'"):
                content = content[1:-1]
            # Extract expressions inside the curly braces and evaluate
            new_content = ""
            parts = re.split(r'({[^}]*})', content)  # Split by expressions in curly braces
            for part in parts:
                if part.startswith("{") and part.endswith("}"):
                    expression = part[1:-1]  # Remove curly braces
                    evaluated = self.eval(expression, {}, self.variables)
                    new_content += str(evaluated)  # Append the evaluated result
                else:
                    new_content += part  # Append the literal text
            return new_content
        else:
            try:
                if any(a in content for a in list(self.variables.keys())) and self.in_class[1]:
                    c = content.split(".")
                    if len(c) > 1:
                        content = c[1]
                conts = self.special_split(content, ",", ("(", "'", '"'), (")", "'", '"'))
                if isinstance(conts, list) and len(conts) > 1:
                    outputs = []
                    for i, val in enumerate(conts):
                        if val.startswith('"') and val.endswith('"') or val.endswith("'") and val.startswith("'"):
                            outputs.append(val[1:-1])
                            
                        else: outputs.append(self.handle_output(val))
                    conts = ""
                    for i in outputs:
                        conts += str(i) + " "
                    return conts
                v = self.eval(content, {}, self.variables)
                if isinstance(content, str) and isinstance(v, tuple):
                    t = ""
                    for i in v:
                        t += str(i) + " "
                    v = t
                    
                return v
            except Exception as e:
                if not self.attempt:
                    print("\033[31mTraceback(most_recent_call_back):\033[0m")
                    for i in self.traceback:
                        print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` line: {self.traceback[i]}, in {i} ],")
                    print(f"    TB - [ File `<{self.path / Path(self.file_name).with_suffix(self.file_extension)}>` TB found > line: {self.og_c} in {i} ]")
                    print(f"\nValueError: Can't access content: '{content}' as it is an undefined Value")
                self.Errors["ValueError"] = True
                return

# This comment right here is only used to copy, i uncomment the lines and copy them to place somewhere in the code later

#if not self.attempt:
#    print("\033[31mTraceback(most_recent_call_back):\033[0m")
#    for i in self.traceback:
#        print(f"    TB - [ File `<{self.path + '/' + self.file_name_name + '.npp'}>` line: {self.traceback[i]}, in {i} ],")
#        print(f"    TB - [ File `<{self.path + '/' + self.file_name_name + '.npp'}>` TB found > line: {self.og_c} in {i} ]")
#        print(f"\nError: ")
#        self.Errors["Error"] = True
#    return None
        