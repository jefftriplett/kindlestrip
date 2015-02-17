===============================
kindlestrip
===============================

A pip-installable conversion of Paul Durrant's kindlestrip library to strip the penultimate record from a Mobipocket file. (http://www.mobileread.com/forums/showthread.php?t=96903)


Usage
-----

To install:

.. code-block:: bash

    $ pip install kindlestrip

To use:

.. code-block:: bash

    $ kindlestrip input.mobi output.mobi

    $ du -sh *
    268K    input.mobi
    200K    output.mobi
