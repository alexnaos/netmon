#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовые тесты для netmon проекта.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import network_data as nd

class TestNetworkData(unittest.TestCase):
    """Тесты для модуля network_data.py."""
    
    def test_devices_structure(self):
        """Проверка структуры данных устройств."""
        self.assertIsInstance(nd.DEVICES, list)
        self.assertGreater(len(nd.DEVICES), 0)
        
        for device in nd.DEVICES:
            self.assertIn("ip", device)
            self.assertIn("name", device)
            self.assertIn("mac", device)
            self.assertIn("category", device)
            self.assertIn("status", device)
    
    def test_connections_structure(self):
        """Проверка структуры соединений."""
        self.assertIsInstance(nd.CONNECTIONS, list)
        
        for conn in nd.CONNECTIONS:
            self.assertIn("from", conn)
            self.assertIn("to", conn)
            self.assertIn("type", conn)
    
    def test_services_structure(self):
        """Проверка структуры сервисов."""
        self.assertIsInstance(nd.DEVICE_SERVICES, dict)
        
        for ip, services in nd.DEVICE_SERVICES.items():
            self.assertIsInstance(services, list)
            for service in services:
                self.assertIn("name", service)
                self.assertIn("type", service)
                self.assertIn("port", service)
                self.assertIn("url", service)
    
    def test_no_duplicate_ips(self):
        """Проверка отсутствия дублирующихся IP-адресов."""
        ips = set()
        for device in nd.DEVICES:
            ip = device["ip"]
            if not ip.startswith("192.168.1."):
                ip = "192.168.1." + ip
            self.assertNotIn(ip, ips, f"Дублирование IP: {ip}")
            ips.add(ip)

class TestIPValidation(unittest.TestCase):
    """Тесты валидации IP-адресов."""
    
    def test_ip_format(self):
        """Проверка формата IP-адресов в DEVICES."""
        for device in nd.DEVICES:
            ip = device["ip"]
            # IP может быть в формате "1" или "192.168.1.1"
            if "." in ip:
                parts = ip.split(".")
                self.assertEqual(len(parts), 4)
                for part in parts:
                    self.assertTrue(0 <= int(part) <= 255)
            else:
                self.assertTrue(1 <= int(ip) <= 254)

if __name__ == "__main__":
    unittest.main()