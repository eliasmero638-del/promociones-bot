# Trigger deployment: verified real commit

# Migración de BOT_TOKEN: el bot ahora opera bajo un nuevo token de Telegram.
# El token se configura como variable de entorno BOT_TOKEN en Railway; no se
# modificó ninguna lógica del proyecto.

# Re-forzar despliegue: Railway había quedado corriendo un despliegue manual
# anterior (commit a7a1b31, de antes de los PRs #29/#30) en vez de la punta
# real de main. Este commit fuerza que Railway vuelva a construir desde el
# código más reciente.
