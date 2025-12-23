# ExternalMCPProvider AsyncIO Fix

## Проблема
Клас `ExternalMCPProvider` не мав методу `disconnect()`, що призводило до помилок при закритті з'єднання з MCP серверами та неправильної обробки ресурсів asyncio.

**Помилка в логах:**
```
'ExternalMCPProvider' object has no attribute 'disconnect'
```

## Виправлення

Додано наступні методи до класу `ExternalMCPProvider` в файлі `core/mcp.py`:

### 1. Ініціалізація додаткових атрибутів
```python
self._exit_stack = None
self._session = None
```
Ці атрибути тепер ініціалізуються в `__init__` для безпечного використання в методах закриття.

### 2. Метод `disconnect()`
```python
def disconnect(self):
    """Properly disconnect from the MCP server and cleanup resources."""
    if not self._connected:
        return
    
    try:
        future = asyncio.run_coroutine_threadsafe(self._async_disconnect(), self._loop)
        future.result(timeout=10)
    except Exception as e:
        print(f"Warning: Error during disconnect: {e}")
    finally:
        self._connected = False
```

**Функціональність:**
- Перевіряє чи є активне з'єднання
- Викликає асинхронне закриття через event loop
- Обробляє помилки без падіння програми
- Гарантує встановлення `_connected = False`

### 3. Асинхронний метод `_async_disconnect()`
```python
async def _async_disconnect(self):
    """Async cleanup of MCP connection."""
    if self._exit_stack:
        try:
            await self._exit_stack.aclose()
        except Exception as e:
            print(f"Warning: Error closing exit stack: {e}")
        finally:
            self._exit_stack = None
            self._session = None
```

**Функціональність:**
- Закриває AsyncExitStack правильно
- Очищає ресурси сесії
- Обробляє помилки під час закриття

### 4. Метод `__del__()`
```python
def __del__(self):
    """Cleanup when object is destroyed."""
    if self._connected:
        self.disconnect()
    
    # Stop the event loop if it's running
    if self._loop and self._loop.is_running():
        self._loop.call_soon_threadsafe(self._loop.stop)
```

**Функціональність:**
- Автоматично закриває з'єднання при видаленні об'єкта
- Зупиняє event loop для уникнення витоку ресурсів
- Гарантує очищення навіть якщо `disconnect()` не був викликаний явно

## Тестування

Створено тест для перевірки функціональності:
```bash
python test_disconnect_simple.py
```

**Результати тестування:**
✅ Метод disconnect існує
✅ Метод disconnect можна викликати
✅ disconnect працює без активного з'єднання
✅ Метод __del__ існує
✅ __del__ можна викликати

## Переваги виправлення

1. **Правильна обробка ресурсів**: AsyncExitStack закривається правильно
2. **Уникнення витоку пам'яті**: Event loop зупиняється при видаленні об'єкта
3. **Безпека**: Всі помилки обробляються gracefully
4. **Сумісність**: Існуючий код продовжує працювати
5. **Тести проходять**: Виправлено помилку в test_mcp_browser.py

## Файли змінено
- `core/mcp.py` - додано методи disconnect, _async_disconnect, __del__

## Дата виправлення
2025-12-21
