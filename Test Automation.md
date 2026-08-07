## Linting and Test Automation

We use Black and Ruff for code checking and linting. Testing is implementing
using PyTest

Test automation can be found in ciscripts/code-fix.sh

Typical output is as follows:

<pre>
img-data$ ci-scripts/code-fix.sh
Formatting with Black...
reformatted /home/kwd/Projects/img-data/tests/test_cli_json.py
reformatted /home/kwd/Projects/img-data/tests/test_cli_inspect.py
reformatted /home/kwd/Projects/img-data/tests/test_cli_strip.py

All done! ✨ 🍰 ✨
3 files reformatted, 16 files left unchanged.

Linting with Ruff...
All checks passed!

Running tests...
======================================= test session starts =======================================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
/img-data
configfile: pyproject.toml
testpaths: tests
collected 138 items                                                                               

tests/test_cli_inspect.py ..............                                                    [ 10%]
tests/test_cli_json.py ......                                                               [ 14%]
tests/test_cli_strip.py ..................                                                  [ 27%]
tests/test_container_inspector.py ...................                                       [ 41%]
tests/test_exif_inspector.py ....................                                           [ 55%]
tests/test_inspector.py .....................................                               [ 82%]
tests/test_json_presentation.py .........                                                   [ 89%]
tests/test_stripper.py ...............                                                      [100%]

====================================== 138 passed in 12.50s =======================================

✓ Code formatted and verified.
(.venv) img-data$ 
</pre>
