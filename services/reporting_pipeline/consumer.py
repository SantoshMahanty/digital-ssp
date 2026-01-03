import asyncio
from aiokafka import AIOKafkaConsumer


async def main():
  consumer = AIOKafkaConsumer(
    'events',
    bootstrap_servers='localhost:9093',
    group_id='reporting',
    enable_auto_commit=True,
  )
  await consumer.start()
  try:
    async for msg in consumer:
      print('event', msg.value.decode('utf-8'))
      # TODO: aggregate and write to ClickHouse/warehouse.
  finally:
    await consumer.stop()


if __name__ == '__main__':
  asyncio.run(main())
