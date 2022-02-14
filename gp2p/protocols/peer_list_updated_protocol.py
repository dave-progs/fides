from typing import List

from gp2p.messaging.network_bridge import NetworkBridge
from gp2p.model.peer import PeerInfo
from gp2p.persistance.trust import TrustDatabase
from gp2p.protocols.recommendation_protocol import RecommendationProtocol
from gp2p.protocols.trust_protocol import TrustProtocol


class PeerListUpdateProtocol:
    """Protocol handling situations when peer list was updated."""

    def __init__(self,
                 trust_db: TrustDatabase,
                 bridge: NetworkBridge,
                 recommendation_protocol: RecommendationProtocol,
                 trust_protocol: TrustProtocol
                 ):
        self.__trust_db = trust_db
        self.__bridge = bridge
        self.__recommendation_protocol = recommendation_protocol
        self.__trust_protocol = trust_protocol

    def peer_list_updated(self, peers: List[PeerInfo]):
        """Processes updated peer list."""
        # first store them in the database
        self.__trust_db.store_connected_peers_list(peers)
        # and now find their trust metrics to send it to the network module
        trust_data = self.__trust_db.get_peers_trust_data([p.id for p in peers])
        # if we don't have data for all peers that means that there are some new peers
        # we need to establish initial trust for them
        if len(trust_data) != len(peers):
            known_peers = {p.peer_id for p in trust_data}
            for peer in [p for p in peers if p.id not in known_peers]:
                # this stores trust in database as well, do not get recommendations because at this point
                # we don't have correct peer list in database
                self.__trust_protocol.determine_initial_trust(peer, get_recommendations=False)
                # TODO: add logic when to get recommendations
                # get recommendations for this peer
                self.__recommendation_protocol.get_recommendation_for(peer, list(known_peers))

            # now when all trust data are in database, let's re-fetch it
            trust_data = self.__trust_db.get_peers_trust_data([p.id for p in peers])
        # dispatch reply
        reliability = {p.peer_id: p.service_trust for p in trust_data}
        self.__bridge.send_peers_reliability(reliability)
        # now set update peer list in database
        self.__trust_db.store_connected_peers_list(peers)
