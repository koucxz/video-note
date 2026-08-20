import pathlib

settings = pathlib.Path(r"D:\code\video-note\src\config\settings.py")
t = settings.read_text(encoding="utf-8")

old = 'return {"type": self.type, "model": self.model, "base_url": self.base_url, "api_key_set": bool(self.api_key)}'
new = 'return {"type": self.type, "model": self.model, "base_url": self.base_url, "api_key": self.api_key, "api_key_set": bool(self.api_key)}'
t = t.replace(old, new, 1)

t = t.replace(
    'return {"enabled": self.enabled, "model": self.model, "base_url": self.base_url, "api_key_set": bool(self.api_key)}',
    'return {"enabled": self.enabled, "model": self.model, "base_url": self.base_url, "api_key": self.api_key, "api_key_set": bool(self.api_key)}'
)

settings.write_text(t, encoding="utf-8")
print("done")
