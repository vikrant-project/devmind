# Safety
- Content classifier refuses keyloggers, phishing, malware, ddos, spam, network attack tools, surveillance.
- Shell blocklist: rm -rf /, dd, mkfs, fork bombs, chmod 777 /, curl|bash, /etc/passwd writes, iptables flush, nmap external, ~/.ssh writes.
- Sandbox levels: Docker (preferred) or subprocess with RLIMITs.
- All checks enforced programmatically at agent core; cannot be bypassed by prompt.
