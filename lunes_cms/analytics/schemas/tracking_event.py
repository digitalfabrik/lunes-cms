from typing import TypedDict, Dict, Any


class TrackingEvent(TypedDict):
    """
    Tracking event
    """

    installationId: str
    eventType: str
    timestamp: str
    payload: Dict[str, Any]
