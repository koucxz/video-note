import pathlib

client_path = pathlib.Path(r"D:\code\video-note\frontend\src\api\client.js")
t = client_path.read_text(encoding="utf-8")

# Update getHistory to handle paginated response
old = "export const getHistory = async () => { return (await api.get('/history')).data; };"
new = """export const getHistory = async (page = 1, size = 20) => {
  const resp = (await api.get('/history', { params: { page, size } })).data;
  // Handle both paginated and legacy array response
  if (Array.isArray(resp)) return { items: resp, total: resp.length, page: 1, size: resp.length, pages: 1 };
  return resp;
};
export const getHistoryAll = async () => {
  const resp = await getHistory(1, 10000);
  return resp.items || [];
};"""
t = t.replace(old, new, 1)

client_path.write_text(t, encoding="utf-8")
print("client.js pagination patched")
