export async function api<T>(path:string, body?:unknown):Promise<T> {
  const response = await fetch(`/api${path}`, body === undefined ? undefined : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '입력값 또는 서버 상태를 확인하세요.');
  return data;
}
