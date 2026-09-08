#!/usr/bin/env bash
# Cria a VM da equipa no Azure for Students (opção a). Requer Azure CLI autenticado: az login
# Uso: EQ=eq01 EMAIL=o.seu@ua.pt ./scripts/azure_vm.sh   (LOC=swedencentral SIZE=Standard_B2als_v2 por omissão)
# Se a subscrição recusar a região ou o tamanho, veja Policy > Assignments (regiões permitidas) e tente B2ts_v2.
set -euo pipefail
EQ=${EQ:-eq01}; RG="rg-sge-$EQ"; VM="vm-sge-$EQ"; LOC=${LOC:-swedencentral}; SIZE=${SIZE:-Standard_B2als_v2}
EMAIL=${EMAIL:?defina EMAIL=o.seu@ua.pt para o aviso de auto-desligar}
az group create -n "$RG" -l "$LOC" -o none
az vm create -g "$RG" -n "$VM" --image Ubuntu2404 --size "$SIZE" --admin-username azureuser --generate-ssh-keys \
  --public-ip-sku Standard --os-disk-size-gb 32 --storage-sku StandardSSD_LRS --custom-data scripts/cloud-init.yaml -o table
az vm open-port -g "$RG" -n "$VM" --port 8069 --priority 1010 -o none
az vm open-port -g "$RG" -n "$VM" --port 8000 --priority 1020 -o none   # aplicação externa (frontend/)
# Auto-desligar diário. A hora é em UTC: 1900 = 20:00 em Lisboa no horário de Verão; mude para 2000 depois de 25 Out.
az vm auto-shutdown -g "$RG" -n "$VM" --time 1900 --email "$EMAIL" -o none
IP=$(az vm show -d -g "$RG" -n "$VM" --query publicIps -o tsv)
echo "VM criada. Ligue-se com: ssh azureuser@$IP   | Odoo em http://$IP:8069 e aplicação externa em http://$IP:8000 depois de: git clone <repo> && cd <repo> && ./scripts/init_db.sh"
echo "A seguir, no portal: Cost Management > Budgets > novo budget de 30 USD no grupo $RG com alertas a 50 % e 80 %; partilhe o grupo com a equipa (Access control (IAM) > Contributor)."
