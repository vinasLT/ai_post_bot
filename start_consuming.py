import asyncio
import signal
from aio_pika import connect_robust
from app.config import settings
from app.core.logger import intercept_stdlib_logging, logger
from app.services.rabbit.rabbit_consumer import RabbitPostsBotConsumer, PostsBotRoutingKeys


async def main():
    intercept_stdlib_logging()
    logger.info(
        "Starting RabbitMQ consumer",
        queue=settings.RABBITMQ_QUEUE_NAME,
        exchange=settings.RABBITMQ_EXCHANGE_NAME,
    )
    connection = await connect_robust(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        consumer = RabbitPostsBotConsumer(connection, [rk.value for rk in PostsBotRoutingKeys])
        await consumer.set_up()
        await consumer.start_consuming()
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for s in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(s, stop_event.set)
            except NotImplementedError:
                pass
        await stop_event.wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
