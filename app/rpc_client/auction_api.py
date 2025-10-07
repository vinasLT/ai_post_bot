import os
import sys
from typing import Any, AsyncGenerator

import grpc

from app.config import settings
from app.core.logger import logger
from app.rpc_client.base_client import BaseRpcClient, T
from app.rpc_client.gen.python.auction.v1.lot_pb2 import Lot

# Ensure generated proto packages (auction, carfax, payment) are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gen', 'python'))

from app.rpc_client.gen.python.auction.v1 import lot_pb2_grpc, lot_pb2


class ApiRpcClient(BaseRpcClient[lot_pb2_grpc.LotServiceStub]):
    def __init__(self):
        super().__init__(server_url=settings.RPC_AUCTION_API_URL)

    async def __aenter__(self):
        await self.connect()
        return self

    def _create_stub(self, channel: grpc.aio.Channel) -> T:
        return lot_pb2_grpc.LotServiceStub(channel)

    async def get_lot_by_vin_or_lot_id(self, vin_or_lot_id: str, site: str = None) -> lot_pb2.GetLotByVinOrLotResponse:
        data = lot_pb2.GetLotByVinOrLotRequest(vin_or_lot_id=vin_or_lot_id, site=site)
        return await self._execute_request(self.stub.GetLotByVinOrLot, data)

    async def get_current_bid(self, lot_id: int, site: str) -> lot_pb2.GetCurrentBidResponse:
        data = lot_pb2.GetCurrentBidRequest(lot_id=lot_id, site=site)
        return await self._execute_request(self.stub.GetCurrentBid, data)

    async def get_sale_history(self, lot_id: int, site: str) -> lot_pb2.GetSaleHistoryResponse:
        data = lot_pb2.GetSaleHistoryRequest(lot_id=lot_id, site=site)
        return await self._execute_request(self.stub.GetSaleHistory, data)

    async def get_average_price(
            self,
            make: str,
            model: str,
            year_from: int,
            year_to: int,
            period: int = 6
    ) -> lot_pb2.GetAveragePriceByMakeModelResponse:
        data = lot_pb2.GetAveragePriceByMakeModelRequest(make=make, model=model, year_from=year_from, year_to=year_to, period=period)
        return await self._execute_request(self.stub.GetAveragePriceByMakeModel, data)
