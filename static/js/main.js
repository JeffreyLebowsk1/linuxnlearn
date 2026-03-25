// LinuxNLearn — main.js  (interactive lesson widgets)

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".interactive-widget").forEach(el => {
    const t = el.dataset.widget;
    if      (t === "terminal")       buildTerminal(el);
    else if (t === "subnet_calc")    buildSubnetCalc(el);
    else if (t === "chmod_calc")     buildChmodCalc(el);
    else if (t === "python_sandbox") buildPythonSandbox(el);
    else if (t === "ios_terminal")   buildIosTerminal(el);
  });

  // Quiz handler
  document.querySelectorAll(".quiz-question").forEach(q => {
    const correct = parseInt(q.dataset.correct, 10);
    q.querySelectorAll(".quiz-option").forEach(btn => {
      btn.addEventListener("click", () => {
        if (q.querySelector(".quiz-option.correct,.quiz-option.wrong")) return;
        const idx = parseInt(btn.dataset.index, 10);
        btn.classList.add(idx === correct ? "correct" : "wrong");
        if (idx !== correct) q.querySelectorAll(".quiz-option")[correct].classList.add("correct");
        q.querySelector(".quiz-feedback").classList.remove("hidden");
      });
    });
  });
});

// ================================================================
// LINUX TERMINAL SIMULATOR
// ================================================================
const CMDS = {
  help: "Available commands (simulated):\n  Navigation : pwd  ls  ls -l  ls -la  cd\n  Files      : cat  head  tail  touch  mkdir  rm  cp  mv\n  Permissions: chmod  chown  ls -l\n  Processes  : ps  ps aux  kill  jobs\n  Network    : ip addr  ip route  ping  ss  dig  nslookup\n  System     : whoami  id  uname  uname -a  hostname  date  uptime  df -h  free -h\n  Type a command and press Enter or click Run.",
  pwd: "/home/student",
  whoami: "student",
  id: "uid=1000(student) gid=1000(student) groups=1000(student),4(adm),27(sudo)",
  hostname: "linux-lab",
  date: () => new Date().toString(),
  uptime: () => {
    const h = Math.floor(Math.random() * 8) + 1;
    const m = String(Math.floor(Math.random() * 60)).padStart(2, "0");
    return " " + new Date().toLocaleTimeString() + "  up " + h + ":" + m + ",  1 user,  load average: 0.12, 0.08, 0.05";
  },
  ls: "Desktop  Documents  Downloads  lab  notes.txt  script.sh",
  "ls -l": "total 40\ndrwxr-xr-x 2 student student 4096 Jan 15 09:00 Desktop\ndrwxr-xr-x 3 student student 4096 Jan 15 09:01 Documents\ndrwxr-xr-x 4 student student 4096 Jan 15 10:00 lab\n-rw-r--r-- 1 student student  512 Jan 15 10:15 notes.txt\n-rwxr-xr-x 1 student student 1024 Jan 15 10:20 script.sh",
  "ls -la": "total 64\ndrwxr-xr-x  8 student student 4096 Jan 15 10:20 .\ndrwxr-xr-x 22 root    root    4096 Jan  1 00:00 ..\n-rw-------  1 student student  612 Jan 15 10:18 .bash_history\n-rw-r--r--  1 student student 3526 Jan  1 00:00 .bashrc\ndrwxr-xr-x  2 student student 4096 Jan 15 09:00 Desktop\ndrwxr-xr-x  4 student student 4096 Jan 15 10:00 lab\n-rw-r--r--  1 student student  512 Jan 15 10:15 notes.txt\n-rwxr-xr-x  1 student student 1024 Jan 15 10:20 script.sh",
  "ls -lah": "total 64K\ndrwxr-xr-x  8 student student 4.0K Jan 15 10:20 .\ndrwxr-xr-x 22 root    root    4.0K Jan  1 00:00 ..\ndrwxr-xr-x  4 student student 4.0K Jan 15 10:00 lab\n-rw-r--r--  1 student student  512 Jan 15 10:15 notes.txt\n-rwxr-xr-x  1 student student 1.0K Jan 15 10:20 script.sh",
  uname: "Linux",
  "uname -a": "Linux linux-lab 6.8.0-49-generic #49-Ubuntu SMP x86_64 GNU/Linux",
  "uname -r": "6.8.0-49-generic",
  "cat /etc/hostname": "linux-lab",
  "cat /etc/os-release": "PRETTY_NAME=\"Ubuntu 24.04 LTS\"\nNAME=\"Ubuntu\"\nVERSION_ID=\"24.04\"",
  "df -h": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   14G   34G  29% /\ntmpfs           3.9G     0  3.9G   0% /dev/shm",
  "free -h": "               total        used        free\nMem:           7.7Gi       1.2Gi       5.1Gi\nSwap:          2.0Gi          0B       2.0Gi",
  "ps aux": "USER         PID %CPU %MEM  COMMAND\nroot           1  0.0  0.1  /sbin/init\nstudent     1024  0.1  0.3  -bash\nstudent     1337  0.0  0.0  ps aux",
  ps: "    PID TTY  CMD\n   1024 pts/0 bash\n   1338 pts/0 ps",
  "ip addr show": "1: lo: <LOOPBACK,UP> mtu 65536\n    inet 127.0.0.1/8 scope host lo\n2: eth0: <BROADCAST,UP> mtu 1500\n    inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic eth0",
  "ip addr": "1: lo: <LOOPBACK,UP>\n    inet 127.0.0.1/8 scope host lo\n2: eth0: <BROADCAST,UP>\n    inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0",
  "ip route show": "default via 192.168.1.1 dev eth0 proto dhcp metric 100\n192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.100",
  "ip route": "default via 192.168.1.1 dev eth0\n192.168.1.0/24 dev eth0 scope link",
  "ss -tuln": "Netid  State   Local Address:Port\nudp    UNCONN  0.0.0.0:68\ntcp    LISTEN  0.0.0.0:22\ntcp    LISTEN  [::]:22",
  "ping -c 4 8.8.8.8": "PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.\n64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=12.4 ms\n64 bytes from 8.8.8.8: icmp_seq=2 ttl=118 time=11.9 ms\n64 bytes from 8.8.8.8: icmp_seq=3 ttl=118 time=12.2 ms\n64 bytes from 8.8.8.8: icmp_seq=4 ttl=118 time=11.8 ms\n--- 8.8.8.8 ping statistics ---\n4 packets transmitted, 4 received, 0% packet loss\nrtt min/avg/max/mdev = 11.8/12.1/12.4/0.2 ms",
  "ping -c 4 192.168.1.1": "PING 192.168.1.1 (192.168.1.1) 56(84) bytes of data.\n64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=0.842 ms\n--- 192.168.1.1 ping statistics ---\n4 packets transmitted, 4 received, 0% packet loss",
  "dig google.com": ";; QUESTION SECTION:\n;google.com.   IN  A\n\n;; ANSWER SECTION:\ngoogle.com.  299  IN  A  142.250.80.46\n\n;; Query time: 14 msec  SERVER: 8.8.8.8",
  "nslookup google.com": "Server: 8.8.8.8\nAddress: 8.8.8.8#53\n\nNon-authoritative answer:\nName: google.com\nAddress: 142.250.80.46",
  "cat /etc/resolv.conf": "nameserver 8.8.8.8\nnameserver 8.8.4.4\nsearch example.local",
  "which python3": "/usr/bin/python3",
  "which bash": "/bin/bash",
  "which ssh": "/usr/bin/ssh",
  "cat notes.txt": "# Lab Notes\n- Practiced ls, cd, pwd\n- Reviewed file permissions\n- Explored /etc directory",
  "chmod 755 script.sh": "", "chmod 600 private.key": "", "chmod +x script.sh": "",
  "echo hello": "hello", "echo $HOME": "/home/student", "echo $SHELL": "/bin/bash",
};

function buildTerminal(container) {
  const uid = Math.random().toString(36).slice(2);
  container.innerHTML =
    '<div class="widget-header">' +
    '<span>&#128187;</span>' +
    '<span class="widget-title">Linux Terminal \u2014 SYS 202 Lab</span>' +
    '<span class="widget-hint">type a command + Enter</span>' +
    '</div>' +
    '<div class="terminal-body" id="tb' + uid + '">' +
    '<p class="terminal-output-line info">SYS 202 lab terminal \u2014 type <span style="color:#67e8f9;font-weight:700">help</span> for available commands.</p>' +
    '</div>' +
    '<div class="terminal-input-row">' +
    '<span class="terminal-prompt">student@linux-lab:~\u00a0</span>' +
    '<input class="terminal-input" type="text" autocomplete="off" spellcheck="false" placeholder="type a command\u2026">' +
    '<button class="terminal-run-btn">Run &#8629;</button>' +
    '<button class="terminal-clear-btn">Clear</button>' +
    '</div>';

  const body = container.querySelector(".terminal-body");
  const inp  = container.querySelector(".terminal-input");
  const hist = []; let hi = -1;

  function run(raw) {
    const cmd = raw.trim();
    if (!cmd) return;
    hist.unshift(cmd); hi = -1;
    aline(body, "student@linux-lab:~$ " + cmd, "cmd");
    const v = CMDS[cmd];
    if (v !== undefined) {
      const o = typeof v === "function" ? v() : v;
      if (o) o.split("\n").forEach(function(l) { aline(body, l, "out"); });
    } else if (cmd.startsWith("echo ")) {
      aline(body, cmd.slice(5).replace(/['"]/g, ""), "out");
    } else if (cmd === "clear") {
      body.innerHTML = "";
    } else if (cmd.startsWith("cd ")) {
      // silently succeed
    } else {
      aline(body, "bash: " + cmd.split(" ")[0] + ": command not found (type 'help')", "err");
    }
    body.scrollTop = body.scrollHeight;
  }

  container.querySelector(".terminal-run-btn").addEventListener("click", function() { run(inp.value); inp.value = ""; inp.focus(); });
  container.querySelector(".terminal-clear-btn").addEventListener("click", function() { body.innerHTML = ""; inp.focus(); });
  inp.addEventListener("keydown", function(e) {
    if (e.key === "Enter")       { run(inp.value); inp.value = ""; }
    else if (e.key === "ArrowUp")  { if (hi < hist.length - 1) inp.value = hist[++hi]; }
    else if (e.key === "ArrowDown"){ if (hi > 0) inp.value = hist[--hi]; else { hi = -1; inp.value = ""; } }
  });
}

function aline(parent, text, cls) {
  var p = document.createElement("p");
  p.className = "terminal-output-line " + cls;
  p.textContent = text;
  parent.appendChild(p);
}

// ================================================================
// SUBNET CALCULATOR
// ================================================================
function buildSubnetCalc(container) {
  container.innerHTML =
    '<div class="widget-header"><span>&#128290;</span><span class="widget-title">IPv4 Subnet Calculator \u2014 NET 201</span></div>' +
    '<div class="subnet-calc-body">' +
    '<div class="subnet-calc-inputs">' +
    '<div class="subnet-calc-field"><label>IP Address</label><input class="sc-ip" type="text" value="192.168.1.0"></div>' +
    '<div class="subnet-calc-field"><label>/ CIDR</label><input class="sc-cidr cidr-input" type="number" value="24" min="0" max="32"></div>' +
    '<button class="subnet-calc-btn sc-btn">Calculate</button>' +
    '</div><div class="sc-results"></div></div>';

  var go = function() { doSubnet(container); };
  container.querySelector(".sc-btn").addEventListener("click", go);
  container.querySelector(".sc-ip").addEventListener("keydown",   function(e) { if (e.key === "Enter") go(); });
  container.querySelector(".sc-cidr").addEventListener("keydown", function(e) { if (e.key === "Enter") go(); });
  go();
}

function doSubnet(c) {
  var ip   = c.querySelector(".sc-ip").value.trim();
  var cidr = parseInt(c.querySelector(".sc-cidr").value, 10);
  var out  = c.querySelector(".sc-results");
  if (!validIP(ip) || isNaN(cidr) || cidr < 0 || cidr > 32) {
    out.innerHTML = '<p class="subnet-error">&#9888; Enter a valid IPv4 address and CIDR (0-32).</p>';
    return;
  }
  var ipI  = ip2i(ip);
  var mask = cidr === 0 ? 0 : (0xFFFFFFFF << (32 - cidr)) >>> 0;
  var wild = (~mask) >>> 0;
  var net  = (ipI & mask) >>> 0;
  var bc   = (net | wild) >>> 0;
  var first = cidr < 31 ? net + 1 : net;
  var last  = cidr < 31 ? bc - 1  : bc;
  var hosts = cidr >= 31 ? Math.pow(2, 32 - cidr) : Math.pow(2, 32 - cidr) - 2;
  out.innerHTML =
    '<div class="subnet-result-grid">' +
    ri("Network",      i2ip(net))   +
    ri("Subnet Mask",  i2ip(mask))  +
    ri("Wildcard",     i2ip(wild))  +
    ri("Broadcast",    i2ip(bc))    +
    ri("First Host",   i2ip(first)) +
    ri("Last Host",    i2ip(last))  +
    ri("Usable Hosts", hosts.toLocaleString()) +
    ri("Total Addrs",  Math.pow(2, 32 - cidr).toLocaleString()) +
    '</div>' +
    '<div class="subnet-binary-row">' +
    '<div class="subnet-result-label">Binary breakdown</div>' +
    '<div class="subnet-result-value">IP:   ' + b32(ipI) + '<br>Mask: ' + b32(mask) + '<br>Net:  ' + b32(net) + '</div>' +
    '</div>';
}

function ri(l, v) { return '<div class="subnet-result-item"><div class="subnet-result-label">' + l + '</div><div class="subnet-result-value">' + v + '</div></div>'; }
function ip2i(s)  { return s.split(".").reduce(function(a, o) { return (a << 8) + parseInt(o, 10); }, 0) >>> 0; }
function i2ip(n)  { return [(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255].join("."); }
function b32(n)   { return [(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255].map(function(o) { return o.toString(2).padStart(8, "0"); }).join("."); }
function validIP(s) { var p = s.split("."); return p.length === 4 && p.every(function(x) { return /^\d+$/.test(x) && +x >= 0 && +x <= 255; }); }

// ================================================================
// CHMOD CALCULATOR
// ================================================================
function buildChmodCalc(container) {
  container.innerHTML =
    '<div class="widget-header"><span>&#128272;</span><span class="widget-title">chmod Permission Calculator \u2014 SYS 202</span></div>' +
    '<div class="chmod-calc-body">' +
    '<table class="chmod-table">' +
    '<thead><tr><th>Who</th><th>Read (r=4)</th><th>Write (w=2)</th><th>Execute (x=1)</th></tr></thead>' +
    '<tbody>' +
    '<tr><td>Owner (u)</td><td><input type="checkbox" class="chk" data-who="u" data-bit="4" checked></td><td><input type="checkbox" class="chk" data-who="u" data-bit="2" checked></td><td><input type="checkbox" class="chk" data-who="u" data-bit="1" checked></td></tr>' +
    '<tr><td>Group (g)</td><td><input type="checkbox" class="chk" data-who="g" data-bit="4" checked></td><td><input type="checkbox" class="chk" data-who="g" data-bit="2"></td><td><input type="checkbox" class="chk" data-who="g" data-bit="1" checked></td></tr>' +
    '<tr><td>Others (o)</td><td><input type="checkbox" class="chk" data-who="o" data-bit="4" checked></td><td><input type="checkbox" class="chk" data-who="o" data-bit="2"></td><td><input type="checkbox" class="chk" data-who="o" data-bit="1" checked></td></tr>' +
    '</tbody></table>' +
    '<div class="chmod-result-row">' +
    '<div class="chmod-octal">755</div>' +
    '<div><div class="chmod-symbolic">rwxr-xr-x</div><div class="chmod-command">chmod 755 &lt;file&gt;</div></div>' +
    '</div></div>';
  container.querySelectorAll(".chk").forEach(function(c) { c.addEventListener("change", function() { updateChmod(container); }); });
  updateChmod(container);
}

function updateChmod(c) {
  var b = { u: 0, g: 0, o: 0 };
  c.querySelectorAll(".chk").forEach(function(x) { if (x.checked) b[x.dataset.who] += parseInt(x.dataset.bit, 10); });
  var oct = "" + b.u + b.g + b.o;
  var sym = sym3(b.u) + sym3(b.g) + sym3(b.o);
  c.querySelector(".chmod-octal").textContent   = oct;
  c.querySelector(".chmod-symbolic").textContent = sym;
  c.querySelector(".chmod-command").textContent  = "chmod " + oct + " <file>";
}
function sym3(n) { return ((n & 4) ? "r" : "-") + ((n & 2) ? "w" : "-") + ((n & 1) ? "x" : "-"); }

// ================================================================
// PYTHON SANDBOX
// ================================================================
function buildPythonSandbox(container) {
  var raw   = decodeURIComponent(container.dataset.code || "");
  var lines = raw.split("\n");
  var code = [], outLines = [], inOut = false;
  for (var i = 0; i < lines.length; i++) {
    var l = lines[i];
    if (!inOut && /^# *(OUTPUT|---)/i.test(l)) { inOut = true; continue; }
    if (inOut) outLines.push(l.replace(/^# ?/, ""));
    else code.push(l);
  }
  container.innerHTML =
    '<div class="widget-header"><span>&#128013;</span><span class="widget-title">Python Sandbox \u2014 CS 215</span></div>' +
    '<div class="python-sandbox-body">' +
    '<pre class="python-sandbox-code">' + esc(code.join("\n").trim()) + '</pre>' +
    '<div class="python-sandbox-run-bar">' +
    '<button class="python-run-btn">&#9654; Run</button>' +
    '<span class="python-run-hint">Click to reveal expected output</span>' +
    '</div>' +
    '<pre class="python-sandbox-output" style="display:none"></pre>' +
    '</div>';
  var o = container.querySelector(".python-sandbox-output");
  container.querySelector(".python-run-btn").addEventListener("click", function() {
    o.textContent = outLines.join("\n").trim() || "(no output)";
    o.style.display = "block";
  });
}

// ================================================================
// CISCO IOS SIMULATOR
// ================================================================
var IOS = {
  USER: {
    enable:                    { next: "PRIV", out: "" },
    "show version":            { out: "Cisco IOS Software, Version 15.9(3)M3\nRouter uptime is 2 hours, 14 minutes\nCisco 2901 with 491520K bytes of memory" },
    "show ip interface brief": { out: "Interface          IP-Address    OK? Status\nGi0/0  192.168.1.1   YES up\nGi0/1  10.0.0.1      YES up\nLoopback0  1.1.1.1  YES up" },
    "?": { out: "enable\nshow\nping\ntraceroute\ndisable\nlogout" },
  },
  PRIV: {
    "configure terminal": { next: "CONFIG", out: "Enter configuration commands, one per line.  End with CNTL/Z." },
    "conf t":             { next: "CONFIG", out: "Enter configuration commands, one per line.  End with CNTL/Z." },
    disable:              { next: "USER",   out: "" },
    "show running-config": { out: "hostname Router\n!\ninterface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0\n no shutdown\n!\nip route 0.0.0.0 0.0.0.0 192.168.1.254\n!\nend" },
    "show ip route":       { out: "S*   0.0.0.0/0 [1/0] via 192.168.1.254\nC    10.0.0.0/24 via GigabitEthernet0/1\nC    192.168.1.0/24 via GigabitEthernet0/0" },
    "show ip interface brief": { out: "Interface          IP-Address    OK? Status\nGi0/0  192.168.1.1   YES up\nGi0/1  10.0.0.1      YES up" },
    "show vlan brief": { out: "VLAN  Name          Status\n1     default       active\n10    Sales         active\n20    Engineering   active\n99    Management    active" },
    "write memory":                       { out: "Building configuration...\n[OK]" },
    "copy running-config startup-config": { out: "Building configuration...\n[OK]" },
    "show arp":          { out: "Internet  192.168.1.254  2  00aa.bbcc.dd01  ARPA  Gi0/0\nInternet  10.0.0.2       1  00aa.bbcc.dd02  ARPA  Gi0/1" },
    "show cdp neighbors":{ out: "Device ID   Local Intf   Holdtme  Platform   Port ID\nSW1         Gig0/0       173      WS-C2960   Gig0/1" },
    "?": { out: "configure terminal\nshow\nwrite memory\ncopy\ndisable\nping\ntraceroute" },
  },
  CONFIG: {
    "hostname R1": { out: "", hostChange: "R1" },
    end:  { next: "PRIV",   out: "" },
    exit: { next: "PRIV",   out: "" },
    "no ip domain-lookup":         { out: "" },
    "service password-encryption": { out: "" },
    "enable secret class":         { out: "" },
    "interface gigabitethernet0/0": { next: "IF", out: "" },
    "interface gi0/0":              { next: "IF", out: "" },
    "interface loopback 0":         { next: "IF", out: "" },
    "vlan 10": { next: "VLAN",   out: "" },
    "vlan 20": { next: "VLAN",   out: "" },
    "vlan 99": { next: "VLAN",   out: "" },
    "router ospf 1":  { next: "ROUTER", out: "" },
    "line console 0": { next: "LINE",   out: "" },
    "line vty 0 4":   { next: "LINE",   out: "" },
    "ip route 0.0.0.0 0.0.0.0 192.168.1.254": { out: "" },
    "?": { out: "hostname\nenable secret\nno ip domain-lookup\ninterface\nvlan\nrouter ospf\nline\nip route\nend\nexit" },
  },
  IF: {
    "ip address 192.168.1.1 255.255.255.0": { out: "" },
    "ip address 10.0.0.1 255.255.255.0":    { out: "" },
    "no shutdown": { out: "%LINK-5-CHANGED: Interface GigabitEthernet0/0, changed state to up" },
    shutdown:      { out: "%LINK-5-CHANGED: Interface GigabitEthernet0/0, changed state to administratively down" },
    "switchport mode access":               { out: "" },
    "switchport mode trunk":                { out: "" },
    "switchport access vlan 10":            { out: "" },
    "switchport trunk allowed vlan 10,20,99": { out: "" },
    "switchport trunk native vlan 99":      { out: "" },
    exit: { next: "CONFIG", out: "" },
    end:  { next: "PRIV",   out: "" },
    "?":  { out: "ip address\nno shutdown\nshutdown\nswitchport\ndescription\nexit\nend" },
  },
  VLAN: {
    "name Sales":       { out: "" },
    "name Engineering": { out: "" },
    "name Management":  { out: "" },
    exit: { next: "CONFIG", out: "" },
    end:  { next: "PRIV",   out: "" },
  },
  ROUTER: {
    "router-id 1.1.1.1":                    { out: "" },
    "network 192.168.1.0 0.0.0.255 area 0": { out: "" },
    "network 10.0.0.0 0.0.0.255 area 0":    { out: "" },
    exit: { next: "CONFIG", out: "" },
    end:  { next: "PRIV",   out: "" },
  },
  LINE: {
    "password cisco":      { out: "" },
    login:                 { out: "" },
    "transport input ssh": { out: "" },
    exit: { next: "CONFIG", out: "" },
    end:  { next: "PRIV",   out: "" },
  },
};

function buildIosTerminal(container) {
  var mode = "USER", hostname = "Router";
  var hist = []; var hi = -1;
  var uid = Math.random().toString(36).slice(2);

  container.innerHTML =
    '<div class="widget-header">' +
    '<span>&#128295;</span>' +
    '<span class="widget-title">Cisco IOS Simulator \u2014 NET 310</span>' +
    '<span class="widget-hint">Type IOS commands. Start: enable</span>' +
    '</div>' +
    '<div class="ios-terminal-body" id="iosb' + uid + '">' +
    '<p class="ios-output-line" style="color:#00cc00">NET 310 IOS Lab \u2014 type <strong>?</strong> for commands in any mode.</p>' +
    '</div>' +
    '<div class="ios-input-row">' +
    '<span class="ios-prompt" id="iosp' + uid + '">Router&gt;\u00a0</span>' +
    '<input class="ios-input" type="text" autocomplete="off" spellcheck="false">' +
    '<button class="terminal-run-btn ios-run-btn">Run &#8629;</button>' +
    '<button class="terminal-clear-btn ios-clr-btn">Clear</button>' +
    '</div>';

  var body = container.querySelector(".ios-terminal-body");
  var inp  = container.querySelector(".ios-input");
  var pr   = container.querySelector(".ios-prompt");

  function upPr() {
    var m = {
      USER:   hostname + ">",
      PRIV:   hostname + "#",
      CONFIG: hostname + "(config)#",
      IF:     hostname + "(config-if)#",
      VLAN:   hostname + "(config-vlan)#",
      ROUTER: hostname + "(config-router)#",
      LINE:   hostname + "(config-line)#"
    };
    pr.textContent = (m[mode] || hostname + ">") + "\u00a0";
  }

  function iline(t) {
    var p = document.createElement("p");
    p.className = "ios-output-line";
    p.textContent = t;
    body.appendChild(p);
  }

  function run(raw) {
    var cmd = raw.trim().toLowerCase().replace(/\s+/g, " ");
    if (!cmd) return;
    hist.unshift(raw.trim()); hi = -1;
    iline(pr.textContent.trim() + " " + raw.trim());
    var tbl = IOS[mode] || {};
    var m   = tbl[cmd];
    if (m !== undefined) {
      if (m.out) m.out.split("\n").forEach(function(l) { iline(l); });
      if (m.next)       { mode = m.next; upPr(); }
      if (m.hostChange) { hostname = m.hostChange; upPr(); }
    } else if (cmd === "end") {
      mode = "PRIV"; upPr();
    } else if (cmd === "exit") {
      if      (mode === "PRIV")   { mode = "USER";   upPr(); }
      else if (mode === "CONFIG") { mode = "PRIV";   upPr(); }
      else if (mode !== "USER")   { mode = "CONFIG"; upPr(); }
    } else if (cmd.startsWith("ping ")) {
      var t = cmd.slice(5);
      iline("Sending 5 ICMP Echos to " + t + ":");
      iline("!!!!!");
      iline("Success rate 100% (5/5), rtt min/avg/max = 1/2/4 ms");
    } else if (cmd.startsWith("description ")) {
      // silently accept
    } else {
      iline("% Unrecognized command (type ? for help)");
    }
    body.scrollTop = body.scrollHeight;
  }

  container.querySelector(".ios-run-btn").addEventListener("click",  function() { run(inp.value); inp.value = ""; inp.focus(); });
  container.querySelector(".ios-clr-btn").addEventListener("click",  function() { body.innerHTML = ""; inp.focus(); });
  inp.addEventListener("keydown", function(e) {
    if (e.key === "Enter")       { run(inp.value); inp.value = ""; }
    else if (e.key === "ArrowUp")  { if (hi < hist.length - 1) inp.value = hist[++hi]; }
    else if (e.key === "ArrowDown"){ if (hi > 0) inp.value = hist[--hi]; else { hi = -1; inp.value = ""; } }
  });
  upPr();
}

function esc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
