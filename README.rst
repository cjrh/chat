chat
====

Demo application for asyncio.


ssl
---

See Doug Hellman's block for how to set up 
the SSL connection. In particular, 
for generating the cert and key:

.. code-block:: bash

    $ openssl req -newkey rsa:2048 -nodes -keyout chat.key \
        -x509 -days 365 -out chat.crt

This creates ``chat.key`` and ``chat.crt`` in the current dir.
