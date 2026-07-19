___
# About
___

Npp (or N++, Nplang) is a transpiled language writen in python.
It is a high level, simple programming language, a project that I have been doing for over a year as a hobby.
Due to sophisticated syntaxes and many supports, I've decided to make it public

Npp includes an easy to read syntax, mainly from python type keywords and C++ like syntaxes.
Simple language features like declarations, instances, keywords, built ins, and OOP.
And many more features N++ includes,
The followings are:
- variable declarations
- function definition
- private and public functions
- Object Oriented Programming
- built in functions and methods
- built in libraries
- self arbritrary codes
- self expression evaluations
- unique built ins
- value types like str, int, float, list, tuple, dict, set

Npp source code is written in Python, but future plans are also thinking about
having backend dependencies of Npp inside C++ for performance utilizations

___
# Syntax
___

Keywords:
- if
- else if
- else
- while
- for
- private
- public
- func
- call
- attempt
- catch
- import
- class
- inherit
- load
- sync
- desync
- open
- break
- continue
- return
- global
- from
- ignore

• Other keywords (mostly used in conditions, loops, etc)
- and
- or
- in
- not
- from
- as
  
___
# special syntaxes
___
• Code blocks - These are defined with curly brackets, { as the starting bracket and } as the ending bracket, this is usually defined at the end of an if, else if, else statement, function definition, class instances, while and for loops, and any that involves code blocks.

• import - libraries are still early stages, but with the "library" folder, you can create your own libraries using python.

• // - this symbol is defined as a comment

• Built in functions - there are built in functions and methods used for easier variable assignments and value manipulations

• OOP - There are multiple syntaxes used for Object Oriented Programming
1. "class" - the main keyword to define a object
2. <const> - the "construction" name, used in
```python
private func <const>(self)
{
    ...
}
```
or as
```python
public func <const>(self)
{
    ...
}
```
this is the construction class, or the initializer, this is where class instances like "self", class attributes, and other more gets defined.
3. "inherit" - The constructor class is also where "inherit" keyword is mostly used, "inherit" gets the attributes, methods, and other more class object information from a Parent class, which is usually defined as
```python
class Child_class(Parent_class1, Parentclass2, ...)
```

___
# Libraries
___
Npp supports custom user built libraries that it can add within the code, and treats it as one
This can be either importing .npp codes
or building your own library (in /library directory) which uses python programs or even deeper, any type of program as long as it follows these instructions
```python
#add this code to /library directory
import ...#import any libraries, modules, etc as dependencies

class any_library_name:
    #the class constructor method must follow this arguments and code
    def __init__(self, library, library_name, variables, Errors, attempt):
        self.library = library
        self.library_name = library_name
        ...
    # this method must also be added
    def process(self, line, variant="ol"):
        if variant == "av": # meaning assign vatiable
            return self.variable_assignment(line) # MUST USE RETURN IF VARIABLE ASSIGNMENT
        else:
            self.one_line_instruction(line)
```
Important notices
- self.process() must be always defined as Npp expects a method named process() with 2 arguments, line and variant.
- variants are 2 types,
- 1. "av" means Assign to Variable, this is defined when there is a code like this
`variable = library.method()`
where "library" is the imported library, "method" is the method of that library (or can be anything like variable assignlents)
and "variable" as the variable name

___
# Setup
___
The setup is simple, you can open up NppIDE.py, a simple notebook like IDE, then after writing the code, save it as .npp, or .nxx, a file extension for Npp
then at npp_interactive_shell, type
`N++ your_file.npp`
to setup Npp, you have to first make a .py python program outside of the directory where Npp is stored.
then write this code
```python
from Npp.npp import NPP

instructions = """
// put your code here
"""
module = {}
npp = NPP(instructions, module)
results = npp.execute()
```
• Key pointers of this code
  1. from Npp.npp import NPP - if Npp in "from Npp.npp..." is a different name, change it immidietly
  2. instructions - must be a doc string
  3. module dictionary - this is where special libraries are stored inside /library directory.
  4. NPP class - the class always expects 1 or 2 arguments, the most important is the "instructions" argument, module argument is optional if you didn't include any libraries from /library directory
  5. npp.execute() - doesn't actually need variable assignments.

for simple debugging, write this on top of the code
```python
from Npp.npp import ndebug
```
then do
```python
npp = NPP(instructions) # or where NPP() gets defined, the code in the following must be added after npp
ndb = ndebug(True) # False for debug mode off
ndb.print_init(npp) # The first print, this prints the variables and values and information
ndb.print_functions(npp) # prints out the each functions, what their code block is, arguments, and information
ndb.print_classes(npp) # prints out the classes and its attributes, methods, and inherited class
```

• This is usefull for simply debugging after code execution to check informations about the program and any issues that needed to be fixed

And For special modules in /library, do this
data_lib for example

```python
from Npp.npp import NPP
from Npp.library.data_lib import class_module

instructions = """
// put your code here
"""
module = {
    "datalib": class_module,
    ...
}
npp = NPP(instructions, module)
results = npp.execute()
```

• key pointers:
- module must have a key with a string, and a name that will be used as the name of the library inside Npp libraries
- "from Npp.library.data_lib" must be imported, and must be the main class
- the module must have the value as a instance of the class object, and don't run the class initialize method

___
# Example Npp Codes
___

• Simple Syntax Examples
```
// double slash as comments
output("Hello, World!") // hello world example
user_input = input("Type in anything: ")
output(user_input)
lst = [2, 6, 4, 9, 8, 1, 3, 0, 5, 7]
tup = (1, 2, 3, 4, 5)
dicts = {"a": 10, "b": 20, "c": 30}
sets = {1, 2, 3, 4, 5}

bif = sort(lst) // built ins
if (dicts["a"] == 10) && (tup[5] == 5)
{
    output("This has 10 and 5")
}
// Curly brackets as code blocks, and functional if statement condition
```
• Calculator code
```
// Calculator
num_a = input("Enter the first number >>> ").as(int)
num_b = input("Enter the second number >>> ").as(int)
operation = input("Enter an operation (+, -, *, /) >>> ")

result = 0

// indentation isn't really necessary

if (operation == "+") {
    result = num_a + num_b
}
else if (operation == "-") {
    result = num_a - num_b
}
else if (operation == "*") {
    result = num_a * num_b
}
else {
    result = num_a * num_b
}
output("Result is:", result)
```

• Bubble sort
```
public func bubble(lst)
{
    lens = length(lst)
    for i in range(lens)
    {
        for k in range(lens - 1)
        {
            x = lst[k]
            y = lst[k + 1]
            
            if (x > y)
            {
                load lst[k] = y
                load lst[k + 1] = x
            }
        }
    }
    return lst
}

unsorted_list = [2, 4, 6, 3, 8, 1, 10, 9, 7, 5]
sorted_list = call bubble(unsorted_list)
```
• For loop
```
import time
rename time as t

// Prints from 1 to N
number = input("enter maximum range > ").as(int)

start = t.time()

for cnt in range(1, number)
{
    output(cnt)
}

end = t.time()
est = end - start

output(f("Estimated taken time {est}"))
```
• Guess the number
```

import random
rename random as r

output("Welcome to guess the number game!")
output("guess a number from 1 to 100 > ")

generated = r.randint(1, 100)
while (True) {
    answer = input("You: ").as(int)
    if (answer > generated)
    {
        output("> Too high")
    }
    else if (answer < generated)
    {
        output("> Too low")
    }
    else
    {
        output("You guessed correctly!")
        output("The answer was: ", generated)
        break
    }
}
```

___
# Things to Note
___
- This code was first developed around November of 2024, Where I only had been learning python for about 3 months.
- This transpiled language is a hobby language and project, This project was develop with the purpose of teaching me more about python, programming, debugging, and more
- There are parts of the Npp source code that were written a year ago, where codes weren't structured properly, and some were written a few months ago, when I finally came back to work on to this language, which are structured neatly while still following the design of the program when i first written it.
___
# What to expect
___
- you should expect tons of bugs, errors, and parsing problems. This language is still not bug free
- The language is getting bug fixes and development everyday, updates frequently every week, but sometimes it won't be quick, as I (main contributor) am also busy with other things.
- Most updates are bug fixes, andmajor updates only drops whenever there are minimal bugs left that doesn't occur majorly in most programs
- Npp version 2 might take months or years, as I have plans to rewrite everything all with my current knowledge in programming.
- Testing takes long, as most tests works while some tests doesn't. Each tests are npp test programs, most of the time, I always test after debugging, some of these programs works, while others doesn't. So some bug fixes makes little difference
___
# Updates
___
"npp.py" is where the main source code is located.
Npp gets updates every 1-2 weeks for bug fixes, monthly for features

• Minor updates - Npp will get small features and bug fixes with this updates, Minor updates also includes updates outside of npp.py, built in libraries, or others will also get updates.
• Major updates - Npp gets updates that includes huge features, additions, bug fixes, and even reworks. These updates are mostly rare, sometimes just every few months or a year if I have the time. This type of update is important as it could majorly improve speed, optimizations, future development, or syntaxes.
___
# Plans with Npp
___
- version >1.2.0: planned on focusing mostly on bug fixes that were left in this language
- version >1.5.0: planned on adding more built in libraries, functions, methods, and keywords, and also improve more on file managements and OOP
- version >1.7.0: planned on using backend dependencies with different languages, mostly C++ or Java
- version >2.0.0: planned on Npp rework, with 3 key planned programs.
  1. Full python rework - Npp source code gets rework in the same environment
  2. Multi language rework - Npp source codes get split across multiple language, each with their own purposes and responsibility, but the main idea is still in python
  3. Compiler rework - 2 types, either Npp code gets translated into machine code like a compiler or in a VM, or fully rewriten somewhere like C++
