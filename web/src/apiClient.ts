export async function requestApi(path: string, body: unknown, token: string) {
  const response = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const responseText = await response.text();
  let responseData: any;
  try {
    responseData = JSON.parse(responseText);
  } catch {
    throw new Error(response.ok
      ? 'The interview service returned an unreadable response.'
      : `Interview service error (${response.status}). Check the FastAPI terminal for details.`);
  }
  if (!response.ok) throw new Error(responseData.detail || `Interview service error (${response.status}).`);
  return responseData;
}
