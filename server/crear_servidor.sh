#!/bin/bash
# Crea el servidor "clipero" en Oracle Cloud (Always Free, Ampere A1) desde Cloud Shell
# y reintenta hasta que Oracle tenga capacidad. Uso:
#   bash <(curl -sL https://raw.githubusercontent.com/eliasmero638-del/promociones-bot/clipero/server/crear_servidor.sh)
# Opcional: OCPUS=2 MEM=12 bash <(...)
set -u
C="${OCI_TENANCY:?Esto se debe correr en Oracle Cloud Shell}"
OCPUS="${OCPUS:-4}"; MEM="${MEM:-24}"
q() { oci "$@" 2>/dev/null; }
nada() { [ -z "$1" ] || [ "$1" = "None" ] || [ "$1" = "null" ]; }

echo "== Revisando si ya existe el servidor =="
YA=$(q compute instance list -c "$C" --display-name clipero --lifecycle-state RUNNING --query 'data[0].id' --raw-output)
if ! nada "$YA"; then echo "Ya tienes un servidor 'clipero' funcionando."; exit 0; fi

echo "== Datos de la cuenta =="
AD=$(q iam availability-domain list -c "$C" --query 'data[0].name' --raw-output)
IMG=$(q compute image list -c "$C" --operating-system "Canonical Ubuntu" --operating-system-version "24.04" \
      --shape VM.Standard.A1.Flex --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output)
echo "Zona: $AD"; nada "$IMG" && { echo "No encontré la imagen de Ubuntu 24.04"; exit 1; }

echo "== Red =="
VCN=$(q network vcn list -c "$C" --query 'data[0].id' --raw-output)
if nada "$VCN"; then
  VCN=$(q network vcn create -c "$C" --cidr-block 10.0.0.0/16 --display-name clipero-vcn --wait-for-state AVAILABLE --query 'data.id' --raw-output)
fi
nada "$VCN" && { echo "No pude crear la red"; exit 1; }
IGW=$(q network internet-gateway list -c "$C" --vcn-id "$VCN" --query 'data[0].id' --raw-output)
if nada "$IGW"; then
  IGW=$(q network internet-gateway create -c "$C" --vcn-id "$VCN" --is-enabled true --display-name clipero-igw --wait-for-state AVAILABLE --query 'data.id' --raw-output)
fi
RT=$(q network vcn get --vcn-id "$VCN" --query 'data."default-route-table-id"' --raw-output)
q network route-table update --rt-id "$RT" --force \
  --route-rules "[{\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$IGW\"}]" >/dev/null
SUB=$(q network subnet list -c "$C" --vcn-id "$VCN" --query 'data[?"prohibit-public-ip-on-vnic"==`false`] | [0].id' --raw-output)
if nada "$SUB"; then
  CIDR=$(q network vcn get --vcn-id "$VCN" --query 'data."cidr-block"' --raw-output)
  SUBC="${CIDR%.*/*}"; SUBC="${SUBC%.*}.200.0/24"
  SUB=$(q network subnet create -c "$C" --vcn-id "$VCN" --cidr-block "$SUBC" --display-name clipero-subnet \
        --route-table-id "$RT" --wait-for-state AVAILABLE --query 'data.id' --raw-output)
fi
nada "$SUB" && { echo "No pude crear la subred pública"; exit 1; }
echo "Red lista."

mkdir -p ~/.ssh; [ -f ~/.ssh/clipero ] || ssh-keygen -t ed25519 -N "" -f ~/.ssh/clipero -q
cat > ~/clipero-init.sh <<'INIT'
#!/bin/bash
apt-get update -qq && apt-get install -y -qq git
git clone --depth 1 -b clipero https://github.com/eliasmero638-del/promociones-bot /opt/clipero
bash /opt/clipero/server/install.sh > /var/log/clipero-install.log 2>&1
INIT

echo "== Creando servidor ($OCPUS OCPU / $MEM GB). Si Oracle no tiene espacio, reintento cada minuto. =="
echo "   Deja esta pestaña abierta. Puedes tocar una tecla de vez en cuando para que no se duerma."
n=0
while true; do
  n=$((n+1))
  out=$(oci compute instance launch -c "$C" --availability-domain "$AD" --shape VM.Standard.A1.Flex \
        --shape-config "{\"ocpus\":$OCPUS,\"memoryInGBs\":$MEM}" --image-id "$IMG" --subnet-id "$SUB" \
        --assign-public-ip true --display-name clipero --boot-volume-size-in-gbs 50 \
        --ssh-authorized-keys-file ~/.ssh/clipero.pub --user-data-file ~/clipero-init.sh 2>&1)
  if echo "$out" | grep -q '"lifecycle-state"'; then
    ID=$(echo "$out" | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["id"])')
    echo "¡SERVIDOR CREADO! Esperando que arranque..."
    oci compute instance get --instance-id "$ID" --wait-for-state RUNNING >/dev/null 2>&1
    IP=$(oci compute instance list-vnics --instance-id "$ID" --query 'data[0]."public-ip"' --raw-output 2>/dev/null)
    echo "======================================"
    echo " LISTO. IP pública: $IP"
    echo " El Clipero se instala solo en ~5 minutos."
    echo "======================================"
    break
  fi
  if echo "$out" | grep -qiE "capacity|LimitExceeded|TooManyRequests|InternalError"; then
    printf "Intento %d %s: sin espacio todavía, reintento en 60 s\n" "$n" "$(date +%H:%M:%S)"; sleep 60; continue
  fi
  echo "Intento $n: error distinto:"; echo "$out" | grep -iE '"message"|"code"' | head -3
  echo "Reintento en 2 minutos..."; sleep 120
done
