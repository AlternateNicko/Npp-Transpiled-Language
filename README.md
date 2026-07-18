___
# About
___

N++, Nlang, Npp, Npl

Npp is a transpiled language writen in python.
It is a high level, simple programming language,
with an easy to read syntax, declarations and instances.
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

__________________
# Syntax
__________________

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

# special syntaxes
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







