from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add codes directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codes'))

from alerting import send_dingtalk, send_email, notify_failure, _sanitize_dict


class TestSanitizeDict(unittest.TestCase):
    """测试字典脱敏功能"""
    
    def test_sanitize_sensitive_keys(self):
        """测试敏感字段被正确脱敏"""
        data = {
            "api_key": "secret123",
            "password": "pass123",
            "normal_field": "value",
            "ACCESS_TOKEN": "token123"
        }
        sanitized = _sanitize_dict(data)
        
        self.assertEqual(sanitized["api_key"], "***")
        self.assertEqual(sanitized["password"], "***")
        self.assertEqual(sanitized["normal_field"], "value")
        self.assertEqual(sanitized["ACCESS_TOKEN"], "***")
    
    def test_sanitize_nested_dict(self):
        """测试嵌套字典脱敏"""
        data = {
            "outer": "value",
            "nested": {
                "secret": "hidden",
                "public": "visible"
            }
        }
        sanitized = _sanitize_dict(data)
        
        self.assertEqual(sanitized["outer"], "value")
        self.assertEqual(sanitized["nested"]["secret"], "***")
        self.assertEqual(sanitized["nested"]["public"], "visible")
    
    def test_sanitize_long_strings(self):
        """测试长字符串被截断"""
        data = {
            "long_text": "a" * 100
        }
        sanitized = _sanitize_dict(data)
        
        self.assertTrue(sanitized["long_text"].endswith("..."))
        self.assertLess(len(sanitized["long_text"]), 60)


class TestSendDingTalk(unittest.TestCase):
    """测试钉钉通知功能"""
    
    @patch('alerting.urlopen')
    def test_send_dingtalk_success(self, mock_urlopen):
        """测试成功发送钉钉消息"""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"errcode":0,"errmsg":"ok"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        # Should not raise exception
        send_dingtalk(
            text="Test message",
            webhook="https://oapi.dingtalk.com/robot/send?access_token=test"
        )
        
        # Verify urlopen was called
        self.assertTrue(mock_urlopen.called)
    
    @patch('alerting.urlopen')
    def test_send_dingtalk_with_secret(self, mock_urlopen):
        """测试带 secret 参数的钉钉消息（当前版本应记录警告）"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"errcode":0,"errmsg":"ok"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        # Should not raise exception even with secret
        send_dingtalk(
            text="Test message",
            webhook="https://oapi.dingtalk.com/robot/send?access_token=test",
            secret="test_secret"
        )
        
        self.assertTrue(mock_urlopen.called)


class TestSendEmail(unittest.TestCase):
    """测试邮件通知功能"""
    
    @patch('alerting.smtplib.SMTP_SSL')
    def test_send_email_ssl(self, mock_smtp_ssl):
        """测试 SSL 方式发送邮件（端口 465）"""
        mock_server = MagicMock()
        mock_smtp_ssl.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp_ssl.return_value.__exit__ = Mock(return_value=False)
        
        send_email(
            subject="Test Subject",
            body="Test Body",
            smtp_host="smtp.qq.com",
            smtp_port=465,
            username="test@qq.com",
            password="test_password",
            to_addrs=["recipient@example.com"]
        )
        
        # Verify SMTP_SSL was called
        mock_smtp_ssl.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()
    
    @patch('alerting.smtplib.SMTP')
    def test_send_email_starttls(self, mock_smtp):
        """测试 STARTTLS 方式发送邮件（端口 587）"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)
        
        send_email(
            subject="Test Subject",
            body="Test Body",
            smtp_host="smtp.qq.com",
            smtp_port=587,
            username="test@qq.com",
            password="test_password",
            to_addrs=["recipient@example.com"]
        )
        
        # Verify SMTP was called with starttls
        mock_smtp.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()


class TestNotifyFailure(unittest.TestCase):
    """测试告警通知功能"""
    
    def test_notify_failure_no_env_no_exception(self):
        """测试在没有配置环境变量时不抛出异常"""
        # Clear all related env vars
        env_vars = [
            "DINGTALK_WEBHOOK_URL",
            "DINGTALK_SECRET",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "SMTP_TO"
        ]
        
        with patch.dict(os.environ, {}, clear=False):
            # Remove all alert-related env vars
            for var in env_vars:
                os.environ.pop(var, None)
            
            # Should not raise exception
            try:
                notify_failure({
                    "keyword": "test",
                    "error": "test error",
                    "run_id": "20260121_123456"
                })
            except Exception as e:
                self.fail(f"notify_failure raised exception: {e}")
    
    @patch('alerting.send_dingtalk')
    def test_notify_failure_with_dingtalk_env(self, mock_send_dingtalk):
        """测试配置钉钉环境变量时发送钉钉通知"""
        with patch.dict(os.environ, {
            "DINGTALK_WEBHOOK_URL": "https://oapi.dingtalk.com/robot/send?access_token=test"
        }):
            notify_failure({
                "keyword": "test",
                "error": "test error"
            })
            
            # Verify send_dingtalk was called
            self.assertTrue(mock_send_dingtalk.called)
    
    @patch('alerting.send_email')
    def test_notify_failure_with_email_env(self, mock_send_email):
        """测试配置邮件环境变量时发送邮件通知"""
        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.qq.com",
            "SMTP_PORT": "465",
            "SMTP_USERNAME": "test@qq.com",
            "SMTP_PASSWORD": "test_password",
            "SMTP_TO": "recipient@example.com"
        }):
            notify_failure({
                "keyword": "test",
                "error": "test error"
            })
            
            # Verify send_email was called
            self.assertTrue(mock_send_email.called)
    
    @patch('alerting.send_email')
    @patch('alerting.send_dingtalk')
    def test_notify_failure_both_channels(self, mock_send_dingtalk, mock_send_email):
        """测试同时配置钉钉和邮件时两者都发送"""
        with patch.dict(os.environ, {
            "DINGTALK_WEBHOOK_URL": "https://oapi.dingtalk.com/robot/send?access_token=test",
            "SMTP_HOST": "smtp.qq.com",
            "SMTP_PORT": "465",
            "SMTP_USERNAME": "test@qq.com",
            "SMTP_PASSWORD": "test_password",
            "SMTP_TO": "recipient@example.com"
        }):
            notify_failure({
                "keyword": "test",
                "error": "test error"
            })
            
            # Verify both methods were called
            self.assertTrue(mock_send_dingtalk.called)
            self.assertTrue(mock_send_email.called)
    
    @patch('alerting.send_dingtalk')
    def test_notify_failure_sanitizes_context(self, mock_send_dingtalk):
        """测试告警通知会对上下文进行脱敏"""
        with patch.dict(os.environ, {
            "DINGTALK_WEBHOOK_URL": "https://oapi.dingtalk.com/robot/send?access_token=test"
        }):
            notify_failure({
                "keyword": "test",
                "api_key": "secret123",
                "error": "test error"
            })
            
            # Verify send_dingtalk was called
            self.assertTrue(mock_send_dingtalk.called)
            
            # Get the text argument
            call_args = mock_send_dingtalk.call_args[1] if mock_send_dingtalk.call_args[1] else mock_send_dingtalk.call_args[0]
            text_arg = call_args.get('text') if isinstance(call_args, dict) else call_args[0]
            
            # Verify api_key is sanitized in the text
            self.assertIn("***", text_arg)
            self.assertNotIn("secret123", text_arg)


if __name__ == '__main__':
    unittest.main()
