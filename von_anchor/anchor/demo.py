"""
Copyright 2017-2019 Government of Canada - Public Services and Procurement Canada - buyandsell.gc.ca

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import logging

from os.path import basename

from von_anchor.anchor.base import BaseAnchor
from von_anchor.anchor.holderprover import HolderProver
from von_anchor.anchor.issuer import Issuer
from von_anchor.anchor.origin import Origin
from von_anchor.anchor.smith import AnchorSmith
from von_anchor.anchor.verifier import Verifier
from von_anchor.cache import ArchivableCaches
from von_anchor.error import ClosedPool
from von_anchor.indytween import Role
from von_anchor.nodepool import NodePool
from von_anchor.tails import Tails
from von_anchor.validcfg import validate_config
from von_anchor.wallet import Wallet


LOGGER = logging.getLogger(__name__)


class NominalAnchor(BaseAnchor):
    """
    NominalAnchor demonstrator class needs access to ledger for authenticated encryption and decryption.
    """

    @staticmethod
    def least_role() -> Role:
        """
        Return the indy-sdk null role for a tails sync anchor, which does not need write access.

        :return: USER role
        """

        LOGGER.debug('NominalAnchor.least_role >>>')

        rv = Role.USER

        LOGGER.debug('NominalAnchor.least_role <<< %s', rv)
        return rv


class TrusteeAnchor(AnchorSmith):
    """
    TrusteeAnchor demonstrator class acts as an anchor smith to forge new anchors.
    """


class BCRegistrarAnchor(Origin, Issuer):
    """
    BCRegistrarAnchor demonstrator class acts as an issuer.
    """


class OrgBookAnchor(HolderProver):
    """
    Basic OrgBookAnchor demonstrator class acts as a holder-prover for any of its registrars' credentials.
    """


class OrgHubAnchor(Verifier, Origin, Issuer, OrgBookAnchor):
    """
    OrgHubAnchor demonstrator class acts as an origin, issuer and verifier for its own credentials
    (principally metadata), and as a holder-prover for its own and any of its registrars' credentials.
    """

    def __init__(self, wallet: Wallet, pool: NodePool = None, **kwargs) -> None:
        """
        Initializer for org hub anchor. Retain input parameters; do not open wallet.

        :param wallet: wallet for anchor use
        :param pool: pool for anchor use
        :param config: configuration dict for cache archive behaviour qua Issuer and Verifier roles; e.g.,

        ::

            {
                'parse-caches-on-open': True,
                'archive-holder-prover-caches-on-close': True,
                'archive-verifier-caches-on-close': {
                    'schema_id': [
                        'R17v42T4pk...:2:tombstone:1.2',
                        '9cHbp54C8n...:2:business:2.0',
                        'Pcq76cx6jE...:2:birth_cert:1.0',
                        ...
                    ],
                    'cred_def_id': [
                        'R17v42T4pk...:3:CL:19:tag',
                        '9cHbp54C8n...:3:CL:37:tag',
                        'Pcq76cx6jE...:3:CL:51:tag',
                        ...
                    ]
                    'rev_reg_id': [
                        'R17v42T4pk...:4:R17v42T4pk...:3:CL:19:tag:CL_ACCUM:0',
                        'R17v42T4pk...:4:R17v42T4pk...:3:CL:19:tag:CL_ACCUM:1',
                        '9cHbp54C8n...:4:9cHbp54C8n...:3:CL:37:tag:CL_ACCUM:0',
                        '9cHbp54C8n...:4:9cHbp54C8n...:3:CL:37:tag:CL_ACCUM:1',
                        '9cHbp54C8n...:4:9cHbp54C8n...:3:CL:37:tag:CL_ACCUM:2',
                        ...
                    ]
                }
            }

        :param rrbx: whether revocation registry builder is an external process
        """

        LOGGER.debug('OrgHubAnchor.__init__ >>> wallet: %s, pool: %s, kwargs: %s', wallet, pool, kwargs)

        super().__init__(wallet, pool, **kwargs)

        self._config = kwargs.get('config', {})
        validate_config('org-hub', self._config)

        LOGGER.debug('OrgHubAnchor.__init__ <<<')

    @staticmethod
    def least_role() -> Role:
        """
        Return the indy-sdk TRUST_ANCHOR role for Org Hub anchor.

        :return: TRUST_ANCHOR role
        """

        LOGGER.debug('OrgHubAnchor.least_role >>>')

        rv = Role.TRUST_ANCHOR

        LOGGER.debug('OrgHubAnchor.least_role <<< %s', rv)
        return rv

    async def close(self) -> None:
        """
        Explicit exit. If so configured, populate cache to prove for any creds on schemata,
        cred defs, and rev regs marked of interest in configuration at initialization,
        archive cache, and purge prior cache archives.

        :return: current object
        """

        LOGGER.debug('OrgHubAnchor.close >>>')

        archive_caches = False
        if self.config.get('archive-holder-prover-caches-on-close', False):
            archive_caches = True
            await self.load_cache_for_proof(False)
        if self.config.get('archive-verifier-caches-on-close', {}):
            archive_caches = True
            await self.load_cache_for_verification(False)
        if archive_caches:
            ArchivableCaches.archive(self.dir_cache)
            ArchivableCaches.purge_archives(self.dir_cache, True)

        # Do not close wallet independently: allow for sharing open wallet over many anchor lifetimes
        # await self.wallet.close() #1.7.8
        # Do not close pool independently: let relying party decide when to go on-line and off-line

        for path_rr_id in Tails.links(self._dir_tails):
            rr_id = basename(path_rr_id)
            try:
                await HolderProver._sync_revoc_for_proof(self, rr_id)
            except ClosedPool:
                LOGGER.warning('OrgHubAnchor sync-revoc on close required ledger for %s but pool was closed', rr_id)

        LOGGER.debug('OrgHubAnchor.close <<<')


class SRIAnchor(Verifier, Origin, Issuer):
    """
    SRIAnchor demonstrator class acts as an origin and issuer of its own credentials and a verifier
    of any holder-prover's.
    """

    def __init__(self, wallet: Wallet, pool: NodePool = None, **kwargs) -> None:
        """
        Initializer for SRI anchor. Retain input parameters; do not open wallet.

        :param wallet: wallet for anchor use
        :param pool: pool for anchor use
        :param config: configuration dict for cache archive behaviour qua Verifier role
        :param rrbx: whether revocation registry builder is an external process
        """

        LOGGER.debug('SRIAnchor.__init__ >>> wallet: %s, pool: %s, kwargs: %s', wallet, pool, kwargs)

        super().__init__(wallet, pool, **kwargs)

        LOGGER.debug('SRIAnchor.close <<<')

    @staticmethod
    def least_role() -> Role:
        """
        Return the indy-sdk TRUST_ANCHOR role for SRI anchor.

        :return: TRUST_ANCHOR role
        """

        LOGGER.debug('SRIAnchor.least_role >>>')

        rv = Role.TRUST_ANCHOR

        LOGGER.debug('SRIAnchor.least_role <<< %s', rv)
        return rv
