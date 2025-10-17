## Python Naming Conventions Cheat Sheet

### General Principles

- **Readability is Key:** Python's philosophy emphasizes clear, readable code. Follow conventions to make your code easy for others (and your future self) to understand.
- **Be Consistent:** Once you choose a convention, stick with it throughout your project.
- **PEP 8:** The official style guide for Python code. This cheat sheet is based on PEP 8.

---

### Key Naming Styles

| Style                                | Format                                         | Example             | When to Use                                                                                                                                                                     |
| ------------------------------------ | ---------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`snake_case`**                     | All lowercase, words separated by underscores. | `my_variable`       | **Variables**, **functions**, **methods**                                                                                                                                       |
| **`PascalCase`**                     | Each word capitalized, no separators.          | `MyClass`           | **Classes**                                                                                                                                                                     |
| **`ALL_CAPS`**                       | All uppercase, words separated by underscores. | `MY_CONSTANT`       | **Constants** (values that don't change)                                                                                                                                        |
| **`_single_leading_underscore`**     | Single underscore prefix.                      | `_private_variable` | **Internal Use:** A convention to indicate a variable or method is intended for internal use within a class or module. Python doesn't enforce "private" access, this is a hint. |
| **`__double_leading_underscore`**    | Double underscore prefix.                      | `__name_mangling`   | **Name Mangling:** Used to avoid naming conflicts in subclasses. The interpreter renames the attribute to `_ClassName__attribute`.                                              |
| **`__double_trailing_underscore__`** | Double underscore suffix.                      | `__init__`          | **Special/Magic Methods:** Reserved for methods with specific behavior in Python. (e.g., `__init__`, `__str__`, `__len__`).                                                     |

---

### Naming Convention Details

#### 1. **Variables & Functions**

- Use `snake_case`.
- Avoid single-letter variable names unless it's a simple loop counter (`i`, `j`).
- Choose names that are descriptive and self-documenting.
- **Bad:** `x` (what is `x`?)
- **Good:** `user_age`, `calculate_total_price`

#### 2. **Classes**

- Use `PascalCase`.
- Class names are typically singular nouns.
- **Bad:** `user_manager`, `users`
- **Good:** `User`, `UserManager`

#### 3. **Modules & Packages**

- Use `snake_case`.
- Keep names short, all lowercase, and avoid underscores where possible.
- **Good:** `my_module.py`, `data_processing`

#### 4. **Constants**

- Use `ALL_CAPS` with underscores.
- These are variables intended to be treated as immutable.
- **Example:** `MAX_CONNECTIONS = 10`, `PI = 3.14159`

---

### Special Naming Rules

- **Private Members (convention):** `_my_internal_method()`

  - The single leading underscore is a convention to signal to other developers that this is a private implementation detail. You can still access it from outside the class, but you shouldn't.

- **Name Mangling:** `__my_private_method()`

  - Python renames this method internally to `_MyClass__my_private_method()`. This prevents subclasses from accidentally overriding it. It's generally less common than the single underscore for typical use cases.

- **Reserved Names:** `__init__`, `__str__`, `__add__`

  - These are built-in "dunder" (double underscore) or "magic" methods. Never invent your own names using this convention. They are reserved for special language features.

- **Variable `_`:**
  - A single underscore can be used as a placeholder for a variable you don't intend to use.
  - **Example:** `for _ in range(5):` (if you don't need the loop counter)
  - **Example:** `name, _ = full_name.split(' ')` (if you only need the first name)

---

### Summary Table

| What to Name              | Convention                           | Example                        |
| ------------------------- | ------------------------------------ | ------------------------------ |
| Variables                 | `snake_case`                         | `user_name`, `is_active`       |
| Functions & Methods       | `snake_case`                         | `get_data()`, `process_info()` |
| Classes                   | `PascalCase`                         | `User`, `DataProcessor`        |
| Modules                   | `snake_case` (lowercase, no hyphens) | `my_module.py`, `database.py`  |
| Constants                 | `ALL_CAPS`                           | `MAX_SIZE`, `DEFAULT_TIMEOUT`  |
| Internal Use (convention) | `_single_leading_underscore`         | `_internal_method`             |
| Special/Magic Methods     | `__double_trailing_underscore__`     | `__init__`, `__str__`          |
