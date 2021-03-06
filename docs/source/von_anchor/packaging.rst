****************************
Packaging
****************************

This section discusses the packaging of the demonstrator project into ``von_base``, ``von_anchor``, and ``von_tails``. The following illustration shows the demonstration packages and their content; further subsections elaborate.

.. image:: https://raw.githubusercontent.com/PSPC-SPAC-buyandsell/von_anchor/master/docs/source/pic/package.png
    :align: center
    :alt: Package Diagram

VON Base
###################################

The von_base package encapsulates:

- the (archived and compressed) libindy.so shared library
- the pipenv virtual environment
- the docker components that the indy-sdk uses
- a docker network for von_conx, a (derelict) VON connector reference implementation.

In addition, the package holds figures for this design document and advice on how to migrate the version of indy-sdk library underpinning the von_anchor code base.

VON Anchor
###################################

The VON anchor package comprises the layer using the indy-sdk to implement the anchor code base (see section 3.2) for all actors in scope. The (pure python) von_anchor package, available through pip from pypi.python.org, implements the VON anchor.

VON Tails
###################################

The VON tails package implements a reference tails file server as a Sanic HTTP server on a docker container, plus synchronization scripts for issuer (uploading) and holder-prover (downloading) roles.
