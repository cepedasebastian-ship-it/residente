function toBase64Utf8(str) {
  return btoa(unescape(encodeURIComponent(str)));
}

export async function onRequestPost(context) {
  const { request, env } = context;
  const formData = await request.formData();

  const redirectUrl = new URL('/', request.url);
  redirectUrl.hash = formData.get('_next_hash') || 'contacto';

  if (formData.get('_honey')) {
    return Response.redirect(redirectUrl.toString(), 303);
  }

  const tipo = (formData.get('_tipo') || 'contacto').toString();
  const viaje = (formData.get('viaje') || '').toString();
  const nombre = (formData.get('nombre') || '').toString();
  const email = (formData.get('email') || '').toString();
  const mensaje = (formData.get('mensaje') || '').toString();

  const now = new Date();
  const iso = now.toISOString();
  const safeSlug = iso.replace(/[:.]/g, '-');
  const path = `submissions/${safeSlug}-${tipo}.json`;

  const record = { date: iso, tipo, viaje, nombre, email, mensaje };

  try {
    await fetch(
      `https://api.github.com/repos/cepedasebastian-ship-it/residente/contents/${path}`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          Accept: 'application/vnd.github+json',
          'User-Agent': 'residente-submit-function',
        },
        body: JSON.stringify({
          message: `Nuevo registro: ${tipo} — ${nombre || email}`,
          content: toBase64Utf8(JSON.stringify(record, null, 2)),
        }),
      }
    );
  } catch (e) {
    // if GitHub write fails, still try to notify by email below
  }

  const notifyEmail = env.NOTIFY_EMAIL || 'cepeda.sebastian@gmail.com';
  try {
    await fetch(`https://formsubmit.co/ajax/${notifyEmail}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        _subject: tipo === 'contacto' ? 'Nueva consulta — Experiencia Residente' : `Lista de espera — ${viaje}`,
        tipo,
        viaje,
        nombre,
        email,
        mensaje,
      }),
    });
  } catch (e) {
    // ignore email failure, submission is already saved to the repo
  }

  redirectUrl.searchParams.set('gracias', '1');
  return Response.redirect(redirectUrl.toString(), 303);
}
