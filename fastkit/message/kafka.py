# -*- coding: utf-8 -*-
import json
from kafka import KafkaProducer
from fastkit.logging import logger


class Producer():
    """ Kafka 生产客户端
    """

    def __init__(self,
                 servers_list: list,
                 topic: str,
                 retries: int = 3,
                 **kwargs):
        # 兼容字符串格式
        if isinstance(servers_list, str):
            servers_list = servers_list.split(",")

        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=servers_list,
            retries=retries,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            **kwargs)

    def send(self, msg: dict, topic: str = None, timeout: int = 10):
        if not topic:
            topic = self.topic

        try:
            self.producer.send(topic, msg).get(timeout=timeout)

        except Exception as error:  # pylint: disable=broad-except
            logger.warning(f"消息发送失败：{error}")
            return False

        return True

    def close(self):
        self.producer.close()
