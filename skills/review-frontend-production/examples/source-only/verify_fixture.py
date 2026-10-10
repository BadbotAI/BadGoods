"""Static fixture checks only; does not exercise a browser."""
from html.parser import HTMLParser
from pathlib import Path

class Inspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.labels = []
        self.inputs = []
        self.buttons = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "label": self.labels.append(attrs)
        if tag == "input": self.inputs.append(attrs)
        if tag == "button": self.buttons.append(attrs)

def verify():
    parser = Inspect()
    parser.feed((Path(__file__).parent / "project/index.html").read_text(encoding="utf-8"))
    assert parser.inputs and parser.buttons
    assert all(any(label.get("for") == item.get("id") for label in parser.labels) for item in parser.inputs)
    assert all(button.get("type") == "button" for button in parser.buttons)
    assert all(button.get("aria-label") for button in parser.buttons)
    return "PASS: label association, explicit button type, nonempty aria-label. No browser checks."

if __name__ == "__main__":
    print(verify())
