import pytest
from stolgo.broker import PaperBroker
from stolgo.core.exceptions import BrokerNotImplementedError


def test_paper_raises():
    with pytest.raises(BrokerNotImplementedError):
        PaperBroker().place_order(None)  # type: ignore[arg-type]
