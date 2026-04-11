# KriptoWidget (TradinWidget)

TradingView **Advanced Chart** embed’ini çerçevesiz, sürüklenebilir ve tüm kenarlardan boyutlandırılabilir küçük bir pencerede açan Windows uygulaması (Python + [pywebview](https://github.com/r0x0r/pywebview)).

## Gereksinimler

- Python 3.12 (önerilen) veya 3.11+
- Windows (WinForms + Edge WebView2)

Çalışma zamanı: `requirements.txt` içindeki `pywebview`.

## Çalıştırma

```bash
pip install -r requirements.txt
python main.py
```

İsteğe bağlı argümanlar: `--symbol`, `--interval`, `--timezone`, `--theme`, `--locale`, `--width`, `--height`, `--no-on-top`. Örnek:

```bash
python main.py --symbol BINANCE:BTCUSDT.P --interval 60
```

## Exe derleme

```bash
build_exe.bat
```

Çıktı: `dist\TradinWidget.exe` (PyInstaller, `tradinwidget.spec`).

## Lisans

Proje dosyaları kullanıcıya aittir; TradingView widget kullanımı [TradingView](https://www.tradingview.com/) koşullarına tabidir.
