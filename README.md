![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python) ![Scapy](https://img.shields.io/badge/Scapy-2.x-green) ![GNS3](https://img.shields.io/badge/GNS3-vIOS--L2-orange) ![Lab](https://img.shields.io/badge/Lab-EGALDITO__LAB-red)

# DHCP Starvation Attack

> **Autor:** Edgardy Olivero | **Matrícula:** 20250704
> **Laboratorio:** EGALDITO\_LAB | **Herramienta:** Python 3 + Scapy
> **Repositorio:** [github.com/Edgardy715/DHCP-Starvation](https://github.com/Edgardy715/DHCP-Starvation)

---

## 📋 Objetivo del Laboratorio

Demostrar cómo un atacante puede agotar el pool de direcciones IP de un servidor DHCP legítimo mediante el envío masivo de solicitudes DHCP con MACs falsas, dejando a los clientes reales sin posibilidad de obtener una configuración IP. Este ataque provoca una denegación de servicio en la capa de red y, en combinación con un servidor DHCP rogue, puede abrir la puerta a un ataque DHCP Spoofing posterior.

---

## 🎯 Objetivo del Script

Generar continuamente MACs aleatorias, enviar un DHCP Discover por cada una, escuchar las respuestas del servidor y completar el handshake DORA con un DHCP Request para cada Offer recibido, maximizando el número de IPs confirmadas como robadas del pool. El script usa un hilo de escucha para procesar las respuestas en paralelo mientras el bucle principal sigue enviando nuevos Discovers.

---

## 📁 Estructura del Repositorio

```text
DHCP-Starvation/
├── Script/
│   └── DHCP-Starvation.py                ← Script principal del ataque
├── Mitigacion/
│   └── Mitigacion-DHCP-Starvation.ios    ← Comandos DHCP Snooping + rate limit
├── Conf-Topologia/
│   └── scripts_bases_configs/
│       ├── R1.ios
│       ├── SW1-VTPSERVER.ios
│       └── SW2.ios
├── Topologia/
│   └── Topologia.png
└── README.md
```

---

## ⚙️ Parámetros del Script

| Variable | Valor | Descripción |
|---|---|---|
| `IFACE` | `eth0.10` | Subinterfaz VLAN 10 del atacante. |
| `rand_mac()` | `02:xx:xx:xx:xx:xx` | MAC falsa generada aleatoriamente en cada iteración. |
| `sleep(0.1)` | 100 ms | Intervalo entre Discovers (~10 paquetes por segundo). |
| `leases` | `dict` | Mapa `xid → fake_mac` para correlacionar respuestas DHCP. |
| `confirmadas` | contador | Número de IPs efectivamente robadas tras recibir ACK. |
| `stop_flag` | `Event()` | Bandera para detener el listener de forma limpia. |
| `filter` | `udp port 68` | Filtro de sniff para capturar respuestas DHCP al cliente. |

---

## 🛠️ Requisitos

```bash
# Dependencias
pip install scapy

# Crear subinterfaz VLAN 10
ip link add link eth0 name eth0.10 type vlan id 10
ip link set eth0.10 up

# Ejecutar como root
sudo python3 Script/DHCP-Starvation.py
```

---

## 🔍 Funcionamiento del Script

### Flujo de ejecución

```text
1. Verifica privilegios root.
2. Registra handlers para SIGINT y SIGTERM.
3. Inicia un hilo 'listener' que escucha DHCP Offer y ACK.
4. Bucle principal:
   a. Genera una MAC falsa con rand_mac().
   b. Construye un DHCP Discover con xid aleatorio.
   c. Registra leases[xid] = fake_mac.
   d. Envía el Discover con sendp().
5. response_handler() procesa las respuestas:
   |-- DHCP Offer (tipo 2):
   |   → obtiene IP ofrecida y server_id.
   |   → envía DHCP Request para completar DORA.
   └── DHCP ACK (tipo 5):
       → incrementa confirmadas.
       → imprime la IP robada en pantalla.
6. Ctrl+C → cleanup(): imprime resumen final.
```

### Estructura del DHCP Discover enviado

```text
[Ether]   src=fake_mac   dst=ff:ff:ff:ff:ff:ff
  [IP]    src=0.0.0.0    dst=255.255.255.255
    [UDP] sport=68       dport=67
      [BOOTP] op=1       chaddr=fake_mac_bytes   xid=aleatorio
        [DHCP] options: message-type=discover
```

### Handshake DORA completado por iteración

```text
Atacante (fake_mac)           R1 (servidor DHCP)
   |─── Discover (xid=N) ───►|
   |◄── Offer (IP=x.x.x.Y) ──|
   |─── Request (acepta Y) ──►|
   |◄── ACK (IP confirmada) ──|
   confirmadas++
   (siguiente iteración con nueva MAC)
```

---

## 🌐 Documentación de la Red

### Topología del Laboratorio

```text
+------------------+        +---------------------+        +---------------------+
|   Kali Linux     |        |        SW2          |        |        SW1          |
|   (Atacante)     |◄──────►|  GNS3 vIOS-L2       |◄──────►|  GNS3 vIOS-L2       |
|  eth0 / eth0.10  | Gi0/1  | VTP Client          | Gi0/0  | VTP Server          |
| 0c:bf:c5:c2:00:00|        | 0cc0.7fb8.0000      |        | 0cb5.a4d7.0000      |
+------------------+        +---------------------+        +---------------------+
                                                                    | Gi0/1
                                                         +---------------------+
                                                         |         R1          |
                                                         |  192.168.10.1/24    |
                                                         +---------------------+
```

> Topología completa disponible en `Topologia/Topologia.png`

### Tabla de Direccionamiento

| Dispositivo | Interfaz | VLAN | IP / Máscara | MAC | Rol |
|---|---|---|---|---|---|
| Kali Linux | `eth0.10` | 10 | 192.168.10.x/24 | `0c:bf:c5:c2:00:00` | Atacante |
| SW1 | Gi0/0 (trunk) | 1, 10 | — | `0cb5.a4d7.0000` | VTP Server / Root Bridge |
| SW2 | Gi0/1 (acceso) | 1, 10 | — | `0cc0.7fb8.0000` | VTP Client |
| R1 | Gi0/0 | 10 | 192.168.10.1/24 | — | Gateway / DHCP Server |

```text
VTP Domain  : EGALDITO_LAB
SW1         : VTP Server | STP Root Bridge | Priority 32769 | MAC 0cb5.a4d7.0000
SW2         : VTP Client
VLAN 10     : RED_LOCAL — 192.168.10.0/24
```

---

## 🛡️ Contramedidas

El archivo de mitigación está en `Mitigacion/Mitigacion-DHCP-Starvation.ios`.

### 1. DHCP Snooping con Rate Limiting — defensa principal

```cisco
en
conf term
ip dhcp snooping
ip dhcp snooping vlan 10

! Puerto hacia el servidor DHCP legítimo (R1) = trusted
interface GigabitEthernet0/0
 ip dhcp snooping trust
exit

! Puerto del atacante = untrusted, limitar a 10 pkt/seg
interface GigabitEthernet0/1
 ip dhcp snooping limit rate 10
exit
do wr
```

> DHCP Snooping construye una tabla de bindings IP-MAC-Puerto y bloquea mensajes DHCP desde puertos no confiables. El rate limiting restringe la cantidad de paquetes DHCP que un atacante puede enviar por segundo, haciendo inviable el agotamiento del pool.
>
> **Nota:** La mitigación se aplica sobre `vlan 10` porque es la VLAN donde el script realiza el ataque (`eth0.10`). Aplicarla solo en VLAN 1 no protegería el pool de VLAN 10.

### 2. Port Security — defensa complementaria

```cisco
interface GigabitEthernet0/1
 switchport port-security
 switchport port-security maximum 3
 switchport port-security violation restrict
 switchport port-security mac-address sticky
```

> Limita el número de MACs distintas que pueden originar tráfico desde ese puerto, reduciendo la efectividad del ataque aunque DHCP Snooping no esté activo.

### Verificación

```cisco
SW2# show ip dhcp snooping
SW2# show ip dhcp snooping statistics
```

---

## 🎬 Video Demostrativo

**Lista de reproducción EGALDITO\_LAB — Layer 2 Network Attacks:**
[https://www.youtube.com/playlist?list=PL24FUvJVT9rBmlkIyA1pGp28VHhh3JK1j](https://www.youtube.com/playlist?list=PL24FUvJVT9rBmlkIyA1pGp28VHhh3JK1j)

**Video de este ataque:**
[https://youtu.be/rs0KW06O5CU](https://youtu.be/rs0KW06O5CU)

---

*Laboratorio desarrollado con fines estrictamente educativos en entorno GNS3 aislado.*
*Autor: Edgardy Olivero | 20250704 | EGALDITO\_LAB*
