from sqlalchemy import select
from sqlalchemy.orm import Session

from stock_agent.app.models.tables import WatchTarget


class WatchTargetRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        symbol: str,
        name: str,
        target_type: str,
        market: str = "CN",
        enabled: bool = True,
        cooldown_minutes: int = 60,
    ) -> WatchTarget:
        target = WatchTarget(
            symbol=symbol,
            name=name,
            target_type=target_type,
            market=market,
            enabled=enabled,
            cooldown_minutes=cooldown_minutes,
        )
        self.session.add(target)
        self.session.flush()
        return target

    def list_enabled(self) -> list[WatchTarget]:
        statement = select(WatchTarget).where(WatchTarget.enabled.is_(True)).order_by(WatchTarget.symbol)
        return list(self.session.scalars(statement).all())

    def delete(self, target_id: int) -> None:
        target = self.session.get(WatchTarget, target_id)
        if target is None:
            return
        self.session.delete(target)
        self.session.flush()
