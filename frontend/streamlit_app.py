import streamlit as st
import requests
import json
import html

API = "http://localhost:8000"

st.set_page_config(
    page_title="NeuralDesk — AI Support",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

for k, v in {
    "token": None, "role": None, "name": None,
    "customer_id": None, "current_page": "dashboard",
    "selected_ticket": None, "auth_mode": "login",
    "editing_ticket": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body,[data-testid="stAppViewContainer"],[data-testid="stAppViewBlockContainer"]{
    background:#080a12!important;color:#c9cdd8!important;font-family:'Sora',sans-serif!important;}
/* FORCE Streamlit sidebar to stay visible */
section[data-testid="stSidebar"],
[data-testid="stSidebar"]{
    display:block!important;
    visibility:visible!important;
    opacity:1!important;
    width:300px!important;
    min-width:300px!important;
    max-width:300px!important;
    transform:translateX(0)!important;
    margin-left:0!important;
    background:linear-gradient(180deg,rgba(12,15,28,.98),rgba(8,10,18,.98))!important;
    border-right:1px solid rgba(255,255,255,.08)!important;
    box-shadow:14px 0 45px rgba(0,0,0,.22)!important;
}

section[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"]{
    display:block!important;
    visibility:visible!important;
    opacity:1!important;
    width:300px!important;
    min-width:300px!important;
    max-width:300px!important;
    background:transparent!important;
}

/* Hide only the collapse/expand controls, not the sidebar */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[kind="header"]{
    display:none!important;
    visibility:hidden!important;
    pointer-events:none!important;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.45rem!important}
[data-testid="stSidebar"] .stButton>button{
    justify-content:flex-start!important;height:42px!important;border-radius:13px!important;
    font-size:13px!important;padding-left:14px!important;
}
.nd-side-brand{display:flex;align-items:center;gap:.85rem;padding:.75rem .25rem 1.2rem;margin-bottom:.6rem;border-bottom:1px solid rgba(255,255,255,.07)}
.nd-side-logo{width:42px;height:42px;border-radius:15px;background:linear-gradient(135deg,#5b6ef5,#9b59f5);display:flex;align-items:center;justify-content:center;box-shadow:0 16px 35px rgba(91,110,245,.25)}
.nd-side-title{font-size:17px;font-weight:800;color:#fff;letter-spacing:-.4px}.nd-side-sub{font-size:11px;color:#6b7280;margin-top:2px}
.nd-side-section{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.09em;font-weight:700;margin:.7rem .15rem .35rem}
.nd-side-spacer{height:1.2rem;border-bottom:1px solid rgba(255,255,255,.07);margin-bottom:1rem}
.nd-side-user{display:flex;align-items:center;gap:.75rem;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.075);border-radius:16px;padding:.75rem;margin:.5rem 0 .7rem}
.nd-side-user-name{font-size:13px;color:#fff;font-weight:700}.nd-side-user-role{font-size:11px;color:#818cf8;margin-top:2px}
#MainMenu,
footer,
header,
[data-testid="stToolbar"]{
    display:none!important;
}

/* Sidebar collapse control is hidden above */
.block-container{padding:0!important;max-width:100%!important;}
.nd-nav{position:sticky;top:0;z-index:999;background:rgba(8,10,18,0.95);
    backdrop-filter:blur(24px);border-bottom:1px solid rgba(255,255,255,0.06);
    padding:0 2rem;display:flex;align-items:center;height:58px;}
.nd-brand{display:flex;align-items:center;gap:10px;}
.nd-brand-icon{width:32px;height:32px;background:linear-gradient(135deg,#5b6ef5,#9b59f5);
    border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;}
.nd-brand-name{font-size:16px;font-weight:700;color:#fff;letter-spacing:-0.4px;}
.nd-nav-right{display:flex;align-items:center;gap:10px;margin-left:auto;}
.nd-badge{background:rgba(91,110,245,0.12);border:1px solid rgba(91,110,245,0.2);
    color:#818cf8;font-size:11px;font-weight:600;padding:3px 8px;border-radius:20px;}
.nd-badge-red{background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.2);
    color:#f87171;font-size:11px;font-weight:600;padding:3px 8px;border-radius:20px;}
.nd-avatar{width:30px;height:30px;background:linear-gradient(135deg,#5b6ef5,#9b59f5);
    border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-size:12px;font-weight:700;color:#fff;}
.nd-status-dot{width:7px;height:7px;background:#22c55e;border-radius:50%;
    display:inline-block;margin-right:5px;}
.nd-page{padding:2rem 2.5rem;}
.nd-card{background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);
    border-radius:16px;padding:1.4rem 1.6rem;margin-bottom:1rem;}
.nd-section-title{font-size:20px;font-weight:700;color:#fff;letter-spacing:-0.4px;margin-bottom:0.25rem;}
.nd-section-sub{font-size:13px;color:#5c6478;margin-bottom:1.5rem;}
.nd-ticket{display:flex;align-items:center;gap:10px;padding:0.85rem 1.1rem;
    background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);
    border-radius:12px;margin-bottom:0.5rem;flex-wrap:wrap;}
.nd-ticket:hover{border-color:rgba(91,110,245,0.3);}
.nd-ticket-id{font-family:'JetBrains Mono',monospace;font-size:12px;color:#3d4251;min-width:32px;}
.nd-ticket-subject{font-size:14px;font-weight:500;color:#c9cdd8;flex:1;min-width:150px;}
.nd-ticket-meta{font-size:12px;color:#5c6478;margin-left:auto;}
.pill{display:inline-block;font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px;}
.pill-open{background:rgba(251,191,36,0.12);color:#fbbf24;border:1px solid rgba(251,191,36,0.2);}
.pill-progress{background:rgba(59,130,246,0.12);color:#60a5fa;border:1px solid rgba(59,130,246,0.2);}
.pill-resolved{background:rgba(34,197,94,0.12);color:#4ade80;border:1px solid rgba(34,197,94,0.2);}
.pill-escalated{background:rgba(239,68,68,0.12);color:#f87171;border:1px solid rgba(239,68,68,0.2);}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0;}
.dot-urgent{background:#ef4444;box-shadow:0 0 6px rgba(239,68,68,0.6);}
.dot-high{background:#f97316;}
.dot-medium{background:#eab308;}
.dot-low{background:#22c55e;}
.nd-auth-card{background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.08);
    border-radius:20px;padding:2.2rem 2.5rem;backdrop-filter:blur(20px);}
.nd-info{background:rgba(91,110,245,0.06);border:1px solid rgba(91,110,245,0.15);
    border-radius:12px;padding:1rem 1.2rem;font-size:13.5px;color:#818cf8;margin-bottom:1rem;}
.nd-warn{background:rgba(251,191,36,0.06);border:1px solid rgba(251,191,36,0.18);
    border-radius:12px;padding:1rem 1.2rem;font-size:13.5px;color:#fbbf24;margin-bottom:1rem;}
.nd-success{background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.2);
    border-radius:12px;padding:1rem 1.2rem;font-size:13.5px;color:#4ade80;margin-bottom:1rem;}
.nd-danger{background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.2);
    border-radius:12px;padding:1rem 1.2rem;font-size:13.5px;color:#f87171;margin-bottom:1rem;}
.nd-response-box{background:rgba(91,110,245,0.05);border:1px solid rgba(91,110,245,0.2);
    border-radius:14px;padding:1.4rem 1.6rem;margin:1rem 0;line-height:1.8;
    font-size:14px;color:#c9cdd8;white-space:pre-wrap;}
.stButton>button{font-family:'Sora',sans-serif!important;font-weight:500!important;
    border-radius:10px!important;transition:all 0.15s ease!important;}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#5b6ef5,#7c3aed)!important;
    border:none!important;color:#fff!important;}
.stButton>button[kind="secondary"]{background:rgba(255,255,255,0.05)!important;
    border:1px solid rgba(255,255,255,0.1)!important;color:#c9cdd8!important;}
.stTextInput>div>div>input,.stTextArea>div>div>textarea,.stSelectbox>div>div{
    background:rgba(255,255,255,0.04)!important;border:1px solid rgba(255,255,255,0.1)!important;
    color:#c9cdd8!important;border-radius:10px!important;font-family:'Sora',sans-serif!important;}
.stTextInput>label,.stTextArea>label,.stSelectbox>label,.stSlider>label,.stNumberInput>label{
    color:#7d8494!important;font-size:13px!important;}
.stForm{background:transparent!important;border:none!important;}
[data-testid="stFormSubmitButton"]>button{width:100%;font-family:'Sora',sans-serif!important;}
hr{border-color:rgba(255,255,255,0.06)!important;}
.stExpander>div>div{background:rgba(255,255,255,0.025)!important;
    border:1px solid rgba(255,255,255,0.07)!important;border-radius:12px!important;}
[data-testid="stMetricValue"]{color:#fff!important;}
[data-testid="stMetricLabel"]{color:#5c6478!important;}

/* Customer professional layout */
.nd-customer-hero{position:relative;overflow:hidden;background:radial-gradient(circle at 15% 0%,rgba(124,58,237,.28),transparent 32%),radial-gradient(circle at 90% 10%,rgba(14,165,233,.18),transparent 30%),linear-gradient(135deg,rgba(255,255,255,.06),rgba(255,255,255,.025));border:1px solid rgba(255,255,255,.09);border-radius:26px;padding:2rem;margin-bottom:1.2rem;box-shadow:0 18px 60px rgba(0,0,0,.28)}
.nd-hero-title{font-size:30px;font-weight:800;color:#fff;letter-spacing:-.8px;margin-bottom:.35rem}.nd-hero-sub{font-size:13px;color:#9aa3b8;line-height:1.7}.nd-hero-actions{display:flex;gap:.75rem;flex-wrap:wrap;margin-top:1.25rem}.nd-soft-chip{display:inline-flex;align-items:center;gap:.4rem;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);color:#dbe2ff;border-radius:999px;padding:.42rem .75rem;font-size:12px;font-weight:600}.nd-stat-card{background:linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.025));border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:1.1rem 1.2rem;min-height:112px}.nd-stat-label{font-size:12px;color:#737c91;margin-bottom:.55rem}.nd-stat-value{font-size:30px;font-weight:800;color:#fff;letter-spacing:-.8px}.nd-stat-note{font-size:11px;color:#596277;margin-top:.35rem}.nd-panel{background:rgba(255,255,255,.028);border:1px solid rgba(255,255,255,.075);border-radius:22px;padding:1.25rem;margin-bottom:1rem}.nd-panel-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:1rem}.nd-panel-title{font-size:17px;font-weight:750;color:#fff}.nd-panel-sub{font-size:12px;color:#667085;margin-top:.2rem}.nd-ticket-pro{position:relative;background:linear-gradient(135deg,rgba(255,255,255,.05),rgba(255,255,255,.018));border:1px solid rgba(255,255,255,.075);border-radius:18px;padding:1rem 1.1rem;margin-bottom:.8rem;box-shadow:0 12px 32px rgba(0,0,0,.16)}.nd-ticket-pro:hover{border-color:rgba(129,140,248,.38);transform:translateY(-1px);transition:.18s}.nd-ticket-top{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap}.nd-ticket-title{font-size:15px;font-weight:700;color:#eef2ff;flex:1;min-width:220px}.nd-ticket-body{font-size:13px;color:#8e97aa;line-height:1.7;margin:.75rem 0 .85rem}.nd-ticket-foot{display:flex;gap:.55rem;flex-wrap:wrap}.nd-mini{font-size:11px;color:#687386;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.075);padding:.32rem .55rem;border-radius:999px}.nd-form-box{background:linear-gradient(180deg,rgba(91,110,245,.08),rgba(255,255,255,.025));border:1px solid rgba(129,140,248,.16);border-radius:22px;padding:1.35rem}.nd-profile-card{background:radial-gradient(circle at 20% 0%,rgba(91,110,245,.25),transparent 35%),rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.085);border-radius:24px;padding:1.5rem}.nd-profile-avatar{width:86px;height:86px;border-radius:24px;background:linear-gradient(135deg,#5b6ef5,#9b59f5);display:flex;align-items:center;justify-content:center;color:#fff;font-size:30px;font-weight:800;box-shadow:0 18px 40px rgba(91,110,245,.28)}.nd-profile-row{display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.07);padding:.8rem 0;gap:1rem}.nd-profile-row:last-child{border-bottom:0}.nd-profile-label{font-size:12px;color:#677083}.nd-profile-value{font-size:13px;color:#e5e7eb;font-weight:600;text-align:right}


/* ===== Professional structure v2 overrides ===== */
.block-container{padding:0!important;max-width:100%!important}
.nd-page{max-width:1240px;margin:0 auto;padding:1.6rem 1.25rem 3rem!important}
.nd-nav{height:64px;padding:0 1.5rem}
.nd-brand-icon{width:36px;height:36px;border-radius:12px}
.nd-brand-name{font-size:18px}
.nd-nav-right{gap:12px}
hr{margin:0!important}
div[data-testid="column"]{min-width:0}
.nd-customer-hero{padding:1.55rem 1.65rem!important;border-radius:22px!important;margin-bottom:1rem!important}
.nd-hero-title{font-size:26px!important}
.nd-hero-sub{max-width:760px}
.nd-stat-card{min-height:96px!important;padding:1rem 1.05rem!important}
.nd-stat-value{font-size:28px!important}
.nd-panel,.nd-form-box,.nd-profile-card{border-radius:20px!important}
.nd-panel{padding:1.15rem!important}
.nd-ticket-pro{padding:1rem!important;margin-bottom:.7rem!important}
.nd-ticket-title{font-size:14.5px!important}
.nd-ticket-body{font-size:12.8px!important;margin:.55rem 0 .75rem!important}
.nd-form-box{position:sticky;top:82px}
.nd-page-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:1rem;margin-bottom:1rem}
.nd-page-kicker{font-size:12px;color:#818cf8;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:.25rem}
.nd-grid-card{background:linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.022));border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:1.2rem}
.nd-list-row{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.9rem 0;border-bottom:1px solid rgba(255,255,255,.065)}
.nd-list-row:last-child{border-bottom:0}
.nd-muted{color:#737c91;font-size:12.5px;line-height:1.6}
.nd-quick-box{display:flex;gap:.75rem;align-items:flex-start;background:rgba(91,110,245,.07);border:1px solid rgba(129,140,248,.14);border-radius:16px;padding:.9rem;margin-top:.8rem}
.nd-quick-icon{width:34px;height:34px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.08)}
@media(max-width:900px){
    .nd-page{padding:1rem .8rem 2.5rem!important}
    .nd-nav{padding:0 .8rem}
    .nd-nav-right span[style*="font-size:13px"]{display:none}
    .nd-form-box{position:static}
    .nd-page-heading{display:block}

    /* Customer list responsiveness */
    .nd-ticket-top{gap:.5rem}
    .nd-ticket-title{min-width:0}
    .nd-ticket-meta{margin-left:0; width:100%}
    .nd-ticket-foot{width:100%}

    /* Make AI response box easier to scan on mobile */
    .nd-response-box{font-size:13.2px; line-height:1.75}
}


</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def pill(status):
    m = {"open":"pill-open","in_progress":"pill-progress",
         "resolved":"pill-resolved","escalated":"pill-escalated"}
    return '<span class="pill ' + m.get(status,"pill-open") + '">' + status.replace("_"," ").title() + '</span>'

def dot(priority):
    m = {"urgent":"dot-urgent","high":"dot-high","medium":"dot-medium","low":"dot-low"}
    return '<span class="dot ' + m.get(priority,"dot-medium") + '"></span>'

def api_get(path, default=None, timeout=5):
    try:
        r = requests.get(f"{API}{path}", timeout=timeout)
        return r.json() if r.ok else default
    except Exception:
        return default

def tid(t):
    return t.get("id") or t.get("ticket_id")

def tdate(t):
    return (t.get("created_at") or t.get("date") or "")[:10]

def tmsg(t):
    return t.get("description") or t.get("message") or ""

def h(value):
    return html.escape(str(value or ""))

# ── AUTH ──────────────────────────────────────────────────────────────────────
if not st.session_state.token:
    col_l, col_c, col_r = st.columns([1, 1.1, 1])
    with col_c:
        st.markdown("<div style='margin-top:70px;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='display:flex;align-items:center;gap:10px;margin-bottom:2rem;'>"
            "<div style='width:34px;height:34px;background:linear-gradient(135deg,#5b6ef5,#9b59f5);"
            "border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:16px;'>🎯</div>"
            "<span style='font-size:18px;font-weight:700;color:#fff;letter-spacing:-0.3px;'>NeuralDesk</span>"
            "<span style='background:rgba(91,110,245,0.14);color:#818cf8;font-size:10px;font-weight:600;"
            "padding:3px 8px;border-radius:20px;border:1px solid rgba(91,110,245,0.25);'>AI Copilot</span>"
            "</div>"
            "<div class='nd-auth-card'>",
            unsafe_allow_html=True
        )

        mc1, mc2 = st.columns(2)
        with mc1:
            if st.button("Sign In", use_container_width=True,
                         type="primary" if st.session_state.auth_mode == "login" else "secondary",
                         key="mode_login"):
                st.session_state.auth_mode = "login"; st.rerun()
        with mc2:
            if st.button("Create Account", use_container_width=True,
                         type="primary" if st.session_state.auth_mode == "register" else "secondary",
                         key="mode_reg"):
                st.session_state.auth_mode = "register"; st.rerun()

        st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

        if st.session_state.auth_mode == "login":
            with st.form("login_form"):
                f_email    = st.text_input("Email address", placeholder="you@company.com")
                f_password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted  = st.form_submit_button("Sign In →", type="primary", use_container_width=True)
            if submitted:
                if not f_email.strip() or not f_password.strip():
                    st.error("Please enter both email and password.")
                else:
                    try:
                        r = requests.post(f"{API}/auth/login",
                                          json={"email": f_email.strip(), "password": f_password},
                                          timeout=5)
                        if r.ok:
                            d = r.json()
                            st.session_state.token     = d["token"]
                            st.session_state.role      = d["role"]
                            st.session_state.name      = d["name"]
                            st.session_state.auth_mode = "login"
                            if d["role"] == "customer":
                                st.session_state.customer_id  = d.get("customer_id")
                                st.session_state.current_page = "my_tickets"
                            else:
                                st.session_state.current_page = "dashboard"
                            st.rerun()
                        else:
                            st.error("Invalid credentials. Check your email and password.")
                    except Exception:
                        st.error("Cannot connect to backend. Make sure uvicorn is running on port 8000.")
        else:
            with st.form("register_form"):
                c1, c2 = st.columns(2)
                with c1:
                    r_cid   = st.text_input("Customer ID", placeholder="CUST004")
                    r_name  = st.text_input("Full Name",   placeholder="Alice Johnson")
                    r_phone = st.text_input("Phone",       placeholder="+91 9876543210")
                with c2:
                    r_email = st.text_input("Email",    placeholder="alice@email.com")
                    r_pass  = st.text_input("Password", type="password", placeholder="Min 6 chars")
                    r_conf  = st.text_input("Confirm",  type="password", placeholder="••••••••")
                reg_sub = st.form_submit_button("Create Account →", type="primary", use_container_width=True)
            if reg_sub:
                if r_pass != r_conf:
                    st.error("Passwords don't match.")
                elif not all([r_cid.strip(), r_name.strip(), r_email.strip(), r_phone.strip(), r_pass]):
                    st.error("All fields are required.")
                elif len(r_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        r = requests.post(f"{API}/auth/register", json={
                            "customer_id": r_cid.strip(), "name": r_name.strip(),
                            "email": r_email.strip(), "phone_no": r_phone.strip(),
                            "password": r_pass
                        }, timeout=5)
                        if r.ok:
                            d = r.json()
                            st.session_state.token        = d["token"]
                            st.session_state.role         = "customer"
                            st.session_state.name         = d["name"]
                            st.session_state.customer_id  = d["customer_id"]
                            st.session_state.current_page = "my_tickets"
                            st.session_state.auth_mode    = "login"
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Registration failed."))
                    except Exception:
                        st.error("Cannot connect to backend.")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align:center;font-size:12px;color:#3d4251;margin-top:1.2rem;'>"
            "Admin? Use your admin email to sign in.</p>",
            unsafe_allow_html=True
        )
    st.stop()

# ── LOGGED IN ─────────────────────────────────────────────────────────────────
role     = st.session_state.role
name     = st.session_state.name or ""
cid      = st.session_state.customer_id
page     = st.session_state.current_page
initials = "".join(w[0].upper() for w in name.split()[:2]) or "?"

open_c = esc_c = 0
if role == "admin":
    try:
        dash   = requests.get(f"{API}/admin/dashboard", timeout=2).json()
        open_c = dash.get("open_tickets", 0)
        esc_c  = dash.get("open_escalations", 0)
    except Exception:
        pass

# ── NAVBAR — built with string concat to avoid f-string HTML escaping ─────────
role_label  = "Admin" if role == "admin" else "Customer"
role_icon   = "👑" if role == "admin" else "👤"
role_color  = "rgba(239,68,68,0.12)" if role == "admin" else "rgba(91,110,245,0.12)"
role_border = "rgba(239,68,68,0.25)"  if role == "admin" else "rgba(91,110,245,0.25)"
role_text   = "#f87171"               if role == "admin" else "#818cf8"

esc_part  = ('<span class="nd-badge-red">🚨 ' + str(esc_c) + ' Escalation' +
             ('s' if esc_c != 1 else '') + '</span>') if (role == "admin" and esc_c > 0) else ""
open_part = ('<span class="nd-badge">' + str(open_c) + ' Open</span>') if (role == "admin" and open_c > 0) else ""
role_part = ('<span style="background:' + role_color + ';border:1px solid ' + role_border +
             ';color:' + role_text + ';font-size:11px;font-weight:600;padding:3px 8px;border-radius:20px;">' +
             role_icon + ' ' + role_label + '</span>')
name_part = '<span style="font-size:13px;color:#5c6478;">' + name + '</span>'
avatar    = '<div class="nd-avatar">' + initials + '</div>'

navbar_html = (
    '<div class="nd-nav">'
    '<div class="nd-brand">'
    '<div class="nd-brand-icon">🎯</div>'
    '<span class="nd-brand-name">NeuralDesk</span>'
    '</div>'
    '<div class="nd-nav-right">'
    '<span><span class="nd-status-dot"></span>'
    '<span style="font-size:12px;color:#5c6478;">API Live</span></span>'
    + esc_part + open_part + role_part + name_part + avatar +
    '</div>'
    '</div>'
)
st.markdown(navbar_html, unsafe_allow_html=True)

# ── SIDEBAR NAVIGATION ───────────────────────────────────────────────────────
ADMIN_NAV = [
    ("dashboard",   "📊 Dashboard"),
    ("tickets",     "🎫 All Tickets"),
    ("ai_response", "🤖 AI Response"),
    ("knowledge",   "📚 Knowledge"),
    ("escalations", "🚨 Escalations"),
    ("feedback",    "⭐ Feedback"),
    ("agent_logs",  "📋 Logs"),
    ("memory",      "🧠 Memory"),
]
CUSTOMER_NAV = [
    ("my_tickets",  "🎫 My Tickets"),
    ("profile",     "👤 Profile"),
    ("my_memory",   "🧠 My History"),
    ("my_feedback", "⭐ Give Feedback"),
]

nav_pages = ADMIN_NAV if role == "admin" else CUSTOMER_NAV

with st.sidebar:
    st.markdown(
        '<div class="nd-side-brand">'
        '<div class="nd-side-logo">🎯</div>'
        '<div><div class="nd-side-title">NeuralDesk</div>'
        '<div class="nd-side-sub">AI Support Workspace</div></div>'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="nd-side-section">Navigation</div>', unsafe_allow_html=True)

    for pg_id, pg_label in nav_pages:
        if st.button(
            pg_label,
            key="nav_" + pg_id,
            type="primary" if page == pg_id else "secondary",
            use_container_width=True
        ):
            st.session_state.current_page = pg_id
            st.rerun()

    st.markdown('<div class="nd-side-spacer"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="nd-side-user">'
        '<div class="nd-avatar">' + h(initials) + '</div>'
        '<div><div class="nd-side-user-name">' + h(name) + '</div>'
        '<div class="nd-side-user-role">' + h(role_label) + '</div></div>'
        '</div>',
        unsafe_allow_html=True
    )

    if st.button("🚪 Sign Out", key="nav_logout", type="secondary", use_container_width=True):
        for k in ["token", "role", "name", "customer_id", "selected_ticket", "editing_ticket"]:
            st.session_state[k] = None
        st.session_state.current_page = "dashboard"
        st.rerun()

st.markdown('<div class="nd-page">', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if role == "admin" and page == "dashboard":
    st.markdown('<div class="nd-section-title">Admin Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="nd-section-sub">System overview — tickets, escalations, satisfaction</div>', unsafe_allow_html=True)
    try:
        d = requests.get(f"{API}/admin/dashboard", timeout=5).json()
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Tickets",    d.get("total_tickets",0))
        c2.metric("Open",             d.get("open_tickets",0))
        c3.metric("Resolved",         d.get("resolved_tickets",0))
        c4.metric("Escalated",        d.get("escalated_tickets",0))
        c1.metric("Open Escalations", d.get("open_escalations",0))
        c2.metric("Avg Rating",       "⭐ " + str(d.get("avg_satisfaction_rating",0)) + " / 5")
        c3.metric("Customers",        d.get("total_customers",0))
        c4.metric("Unread Alerts",    d.get("unread_notifications",0))
    except Exception as e:
        st.error("Cannot load dashboard: " + str(e))

    st.divider()
    ca, cb = st.columns(2)
    with ca:
        st.markdown('<div class="nd-section-title" style="font-size:16px;">🚨 Open Escalations</div>', unsafe_allow_html=True)
        escs = api_get("/escalations/?status=open", [])
        if not escs:
            st.markdown('<div class="nd-info">✅ No open escalations.</div>', unsafe_allow_html=True)
        for esc in (escs or []):
            with st.expander("Ticket #" + str(esc['ticket_id']) + " — " + esc['reason'][:50]):
                st.write("**Reason:** " + esc['reason'])
                note = st.text_input("Resolution note", key="dash_note_" + str(esc['id']))
                if st.button("✅ Resolve", key="dash_res_" + str(esc['id']), type="primary"):
                    requests.patch(f"{API}/escalations/{esc['id']}/resolve", json={"admin_note": note})
                    st.rerun()
    with cb:
        st.markdown('<div class="nd-section-title" style="font-size:16px;">👥 Registered Customers</div>', unsafe_allow_html=True)
        customers = api_get("/admin/customers", [])
        for c in (customers or []):
            card = ('<div class="nd-card" style="padding:0.7rem 1.1rem;">'
                    '<b style="color:#c9cdd8;">' + c["name"] + '</b> '
                    '<span style="color:#5c6478;font-size:12px;">(' + c["email"] + ')</span><br>'
                    '<code style="color:#818cf8;font-size:11px;">' + c["customer_id"] + '</code>'
                    '</div>')
            st.markdown(card, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — ALL TICKETS
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "admin" and page == "tickets":
    st.markdown('<div class="nd-section-title">All Tickets</div>', unsafe_allow_html=True)
    st.markdown('<div class="nd-section-sub">Manage and respond to all customer support requests</div>', unsafe_allow_html=True)
    status_f = st.selectbox("Filter", ["All","open","in_progress","resolved","escalated"],
                            label_visibility="collapsed")
    tickets  = api_get("/tickets/" + ("?status=" + status_f if status_f != "All" else ""), [])
    st.markdown('<p style="font-size:13px;color:#5c6478;margin-bottom:1rem;">' +
                str(len(tickets or [])) + ' ticket(s)</p>', unsafe_allow_html=True)
    for t in (tickets or []):
        ca, cb = st.columns([5,1])
        with ca:
            row = ('<div class="nd-ticket">'
                   '<span class="nd-ticket-id">#' + str(tid(t)) + '</span>'
                   + dot(t.get("priority","medium"))
                   + '<span class="nd-ticket-subject">' + t.get("subject","—") + '</span>'
                   + pill(t.get("status","open"))
                   + '<span class="nd-ticket-meta">' + t.get("customer_id","—") + ' · ' + tdate(t) + '</span>'
                   '</div>')
            st.markdown(row, unsafe_allow_html=True)
        with cb:
            if st.button("Open →", key="admin_t_" + str(tid(t)), type="primary"):
                st.session_state.selected_ticket = tid(t)
                st.session_state.current_page    = "ai_response"
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — AI RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "admin" and page == "ai_response":
    st.markdown('<div class="nd-section-title">AI Response Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="nd-section-sub">Generate contextual responses using RAG + Memory + CRM + Billing</div>', unsafe_allow_html=True)
    sel = st.session_state.selected_ticket
    ticket_id_input = st.number_input("Ticket ID", min_value=1, step=1, value=int(sel) if sel else 1)
    try:
        r = requests.get(f"{API}/tickets/{ticket_id_input}", timeout=5)
        if not r.ok:
            st.error("Ticket #" + str(ticket_id_input) + " not found.")
            st.stop()
        ticket = r.json()
    except Exception as e:
        st.error("Cannot connect to backend: " + str(e)); st.stop()

    ca, cb = st.columns([3,1])
    with ca:
        st.markdown('<div class="nd-section-title" style="font-size:17px;">#' +
                    str(tid(ticket)) + ' — ' + ticket.get("subject","") + '</div>', unsafe_allow_html=True)
        st.markdown('<p style="color:#5c6478;font-size:13px;margin-bottom:0.8rem;">Customer ID: ' +
                    ticket.get("customer_id","—") + ' · Category: ' +
                    ticket.get("category","—").title() + '</p>', unsafe_allow_html=True)
    with cb:
        st.markdown('<div style="text-align:right;margin-top:0.5rem;">' +
                    pill(ticket.get("status","open")) + '</div>', unsafe_allow_html=True)

    st.markdown('<div class="nd-card"><p style="font-size:12px;color:#5c6478;margin-bottom:0.5rem;">CUSTOMER MESSAGE</p>'
                '<p style="font-size:14px;color:#c9cdd8;line-height:1.7;">' +
                tmsg(ticket) + '</p></div>', unsafe_allow_html=True)

    if ticket.get("memory_context_used"):
        with st.expander("🧠 Memory Context"):
            st.write(ticket["memory_context_used"])
    if ticket.get("kb_sources_used"):
        with st.expander("📚 KB Sources"):
            st.code(ticket["kb_sources_used"])

    st.divider()
    draft = ticket.get("ai_draft_response")
    if not draft:
        st.markdown('<div class="nd-info">No AI draft yet. Click below to run the full pipeline.</div>', unsafe_allow_html=True)
        if st.button("🤖 Generate AI Response", type="primary"):
            with st.spinner("Running: CRM → Billing → RAG → Memory → LLM…"):
                r2 = requests.post(f"{API}/agent/generate/{ticket_id_input}", timeout=600)
            if r2.ok:
                st.success("✅ Draft generated!")
                st.rerun()
            else:
                st.error(r2.text)
    else:
        edited = st.text_area("AI Draft Response (editable):", value=draft, height=280)
        c1,c2,c3 = st.columns(3)
        with c1:
            if st.button("✅ Approve & Save", type="primary"):
                requests.patch(f"{API}/tickets/{ticket_id_input}",
                               json={"agent_final_response": edited, "status":"in_progress"})
                st.success("Response saved!")
                st.rerun()
        with c2:
            if st.button("🔁 Regenerate"):
                with st.spinner("Re-running…"):
                    requests.post(f"{API}/agent/generate/{ticket_id_input}", timeout=600)
                st.rerun()
        with c3:
            if st.button("✅ Resolve & Save Memory", type="primary"):
                r3 = requests.post(f"{API}/agent/resolve/{ticket_id_input}", timeout=30)
                if r3.ok:
                    st.success("✅ Resolved! Memory saved 🧠")
                    st.rerun()
        st.divider()
        with st.form("esc_inline"):
            esc_r = st.text_input("Escalation reason")
            if st.form_submit_button("🚨 Escalate"):
                if esc_r.strip():
                    requests.post(f"{API}/escalations/",
                                  json={"ticket_id":ticket_id_input,"reason":esc_r})
                    st.warning("Ticket escalated.")
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "knowledge":
    st.markdown('<div class="nd-section-title">Knowledge Base</div>', unsafe_allow_html=True)
    stats = api_get("/knowledge/stats", {})
    c1,c2 = st.columns(2)
    c1.metric("Vectors Indexed", stats.get("total_vectors",0))
    c2.metric("Status", stats.get("status","unknown").upper())
    if role == "admin":
        st.divider()
        st.markdown("**Upload Support Document**")
        uploaded = st.file_uploader("Choose a file", type=["pdf","docx","txt","md"], label_visibility="collapsed")
        if uploaded and st.button("⬆ Upload & Index", type="primary"):
            with st.spinner("Indexing " + uploaded.name + "…"):
                r = requests.post(f"{API}/knowledge/upload",
                                  files={"file":(uploaded.name,uploaded,uploaded.type)}, timeout=120)
            if r.ok:
                rj = r.json()
                st.success("✅ " + rj['filename'] + " — " + str(rj['chunks_indexed']) + " chunks indexed!")
            else:
                st.error(r.text)
    else:
        st.markdown('<div class="nd-info">📚 Documents uploaded by admins power the AI responses to your tickets.</div>', unsafe_allow_html=True)
    st.divider()
    docs = api_get("/knowledge/documents", [])
    if not docs:
        st.info("No documents indexed yet.")
    for doc in (docs or []):
        date_val = str(doc.get("uploaded_at") or doc.get("date",""))[:10]
        card = ('<div class="nd-card" style="padding:0.7rem 1.1rem;">'
                '📄 <b style="color:#c9cdd8;">' + doc["filename"] + '</b> — '
                '<span style="color:#5c6478;">' + str(doc.get("chunk_count",0)) + ' chunks</span>'
                '<span style="float:right;font-size:11px;color:#3d4251;">' + date_val + '</span>'
                '</div>')
        st.markdown(card, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — ESCALATIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "admin" and page == "escalations":
    st.markdown('<div class="nd-section-title">Escalation Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="nd-section-sub">Raise, track, and resolve ticket escalations</div>', unsafe_allow_html=True)
    with st.form("esc_create"):
        c1,c2 = st.columns([1,3])
        with c1: esc_tid    = st.number_input("Ticket ID", min_value=1, step=1)
        with c2: esc_reason = st.text_area("Reason", height=80)
        if st.form_submit_button("🚨 Raise Escalation", type="primary"):
            r = requests.post(f"{API}/escalations/", json={"ticket_id":int(esc_tid),"reason":esc_reason})
            st.success("Escalation raised!") if r.ok else st.error(r.text)
            st.rerun()
    st.divider()
    sf   = st.selectbox("Filter", ["All","open","resolved"])
    escs = api_get("/escalations/" + ("?status=" + sf if sf != "All" else ""), [])
    for esc in (escs or []):
        icon = "🔴" if esc["status"] == "open" else "✅"
        with st.expander(icon + " #" + str(esc['id']) + " — Ticket #" + str(esc['ticket_id']) + " · " + esc['reason'][:55]):
            st.write("**Reason:** " + esc['reason'])
            st.write("**Status:** " + esc['status'] + "  |  **Created:** " + esc.get('created_at','')[:10])
            if esc.get("admin_note"):
                st.markdown('<div class="nd-success">✅ Resolution: ' + esc["admin_note"] + '</div>', unsafe_allow_html=True)
            if esc["status"] == "open":
                note = st.text_input("Resolution notes", key="esc_note_" + str(esc['id']))
                if st.button("Mark Resolved ✓", key="esc_r_" + str(esc['id']), type="primary"):
                    requests.patch(f"{API}/escalations/{esc['id']}/resolve", json={"admin_note": note})
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — FEEDBACK
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "admin" and page == "feedback":
    st.markdown('<div class="nd-section-title">Customer Feedback</div>', unsafe_allow_html=True)
    s = api_get("/feedback/stats", {})
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Responses",  s.get("total",0))
    c2.metric("Average Rating",   "⭐ " + str(s.get("average_rating",0)))
    c3.metric("5-Star",           s.get("rating_breakdown",{}).get("5_star",0))
    c4.metric("1-Star",           s.get("rating_breakdown",{}).get("1_star",0))
    st.divider()
    feedbacks = api_get("/feedback/", [])
    if not feedbacks:
        st.info("No feedback submitted yet.")
    for fb in (feedbacks or []):
        stars = "⭐" * fb["rating"]
        with st.expander(stars + " Ticket #" + str(fb['ticket_id']) + " — " + fb.get('subject','') + " · " + fb['created_at'][:10]):
            st.write("**Customer:** " + fb['customer_id'] + "  |  **Rating:** " + str(fb['rating']) + "/5")
            if fb.get("message"):
                st.write("**Message:** " + fb['message'])

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — AGENT LOGS
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "admin" and page == "agent_logs":
    st.markdown('<div class="nd-section-title">Agent Run Logs</div>', unsafe_allow_html=True)
    st.markdown('<div class="nd-section-sub">Every AI action logged — RAG, Memory, CRM, LLM</div>', unsafe_allow_html=True)
    if st.button("🔄 Refresh", type="secondary"):
        st.rerun()
    logs = api_get("/admin/logs?limit=100", [])
    if not logs:
        st.info("No agent logs yet.")
    for log in (logs or []):
        icons = {"CRM Lookup":"🔵","Billing Lookup":"💰","RAG Knowledge Base Search":"📚",
                 "Mem0 Memory Retrieval":"🧠","LLM Response Generation":"🤖","generate_draft_response":"⚡"}
        icon = icons.get(log.get("action",""),"⚙️")
        with st.expander(icon + " Ticket #" + str(log['ticket_id']) + " — " + log['action'] + " — " + log.get('created_at','')[:16]):
            st.write("**Result:** " + str(log.get("result",""))[:400])

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — MEMORY
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "admin" and page == "memory":
    st.markdown('<div class="nd-section-title">Customer Memory Viewer</div>', unsafe_allow_html=True)
    st.markdown('<div class="nd-section-sub">View and manage persistent AI memory</div>', unsafe_allow_html=True)
    mem_cid = st.text_input("Customer ID", placeholder="CUST001")
    c1,c2   = st.columns([2,1])
    with c1:
        load = st.button("Load Memory", type="primary")
    with c2:
        if st.button("🗑 Delete (GDPR)", type="secondary") and mem_cid:
            requests.delete(f"{API}/memory/{mem_cid}")
            st.warning("All memories deleted for " + mem_cid)
    if load and mem_cid:
        mem_data = api_get("/memory/" + mem_cid, {})
        memories = mem_data.get("memories",[]) if isinstance(mem_data,dict) else []
        if not memories:
            st.info("No memories stored for " + mem_cid + " yet.")
        else:
            st.success("Found " + str(len(memories)) + " memories for " + mem_cid)
            for i,m in enumerate(memories,1):
                with st.expander("Memory " + str(i) + " · " + m.get('created_at','')[:10]):
                    st.write(m.get("memory",""))

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOMER — MY TICKETS (professional customer dashboard + submit ticket)
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "customer" and page == "my_tickets":
    all_tix = api_get("/tickets/", []) or []
    my_all = [t for t in all_tix if t.get("customer_id") == cid]

    total_n = len(my_all)
    open_n = sum(1 for t in my_all if t.get("status") == "open")
    progress_n = sum(1 for t in my_all if t.get("status") == "in_progress")
    resolved_n = sum(1 for t in my_all if t.get("status") == "resolved")

    st.markdown(
        '<div class="nd-customer-hero">'
        '<div class="nd-soft-chip">✨ AI-powered support portal</div>'
        '<div class="nd-hero-title">Hello, ' + h(name) + ' 👋</div>'
        '<div class="nd-hero-sub">Track your support requests, view AI responses, submit new issues, and manage your profile from one clean customer dashboard.</div>'
        '<div class="nd-hero-actions">'
        '<span class="nd-soft-chip">Customer ID: <code style="color:#c7d2fe;">' + h(cid) + '</code></span>'
        '<span class="nd-soft-chip">🟢 API Live</span>'
        '<span class="nd-soft-chip">🤖 Automated AI Agent</span>'
        '</div></div>', unsafe_allow_html=True
    )

    s1, s2, s3, s4 = st.columns(4)
    stats = [("Total Tickets", total_n, "All requests"), ("Open", open_n, "Waiting for response"),
             ("In Progress", progress_n, "AI is handling"), ("Resolved", resolved_n, "Completed")]
    for col, (label, value, note) in zip([s1, s2, s3, s4], stats):
        with col:
            st.markdown('<div class="nd-stat-card"><div class="nd-stat-label">' + label + '</div><div class="nd-stat-value">' + str(value) + '</div><div class="nd-stat-note">' + note + '</div></div>', unsafe_allow_html=True)

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    left, right = st.columns([1.45, 1])

    with left:
        st.markdown('<div class="nd-panel"><div class="nd-panel-head"><div><div class="nd-panel-title">🎫 My Tickets</div><div class="nd-panel-sub">Recent requests and support responses</div></div></div>', unsafe_allow_html=True)
        status_f = st.selectbox("Filter tickets", ["All","open","in_progress","resolved","escalated"], label_visibility="collapsed")
        my_tickets = my_all
        if status_f != "All":
            my_tickets = [t for t in my_tickets if t.get("status") == status_f]

        if not my_tickets:
            st.markdown('<div class="nd-info">📭 No tickets found for this filter. Submit a new ticket from the right side.</div>', unsafe_allow_html=True)

        for t in my_tickets:
            t_id = tid(t)
            t_key = str(t_id)
            is_editing = st.session_state.editing_ticket == t_id
            response = t.get("agent_final_response") or t.get("ai_draft_response")
            can_edit = t.get("status") == "open"

            st.markdown(
                '<div class="nd-ticket-pro">'
                '<div class="nd-ticket-top"><span class="nd-ticket-id">#' + h(t_key) + '</span>'
                + dot(t.get("priority","medium")) + '<span class="nd-ticket-title">' + h(t.get("subject","—")) + '</span>'
                + pill(t.get("status","open")) + '</div>'
                '<div class="nd-ticket-body">' + h(tmsg(t)[:180]) + ('...' if len(tmsg(t)) > 180 else '') + '</div>'
                '<div class="nd-ticket-foot"><span class="nd-mini">📅 ' + h(tdate(t) or 'Today') + '</span><span class="nd-mini">🏷 ' + h(t.get("category","general")).title() + '</span><span class="nd-mini">⚡ ' + h(t.get("priority","medium")).title() + '</span></div>'
                '</div>', unsafe_allow_html=True
            )

            b1, b2, b3, b4 = st.columns([1,1,1,5])
            with b1:
                if st.button("👁 View", key="view_" + t_key, type="primary"):
                    st.session_state.selected_ticket = t_id
                    st.session_state.editing_ticket = None
                    st.session_state.current_page = "ticket_view"
                    st.rerun()
            with b2:
                if can_edit and st.button("✏️ Edit" if not is_editing else "✖ Close", key="edit_" + t_key, type="secondary"):
                    st.session_state.editing_ticket = None if is_editing else t_id
                    st.rerun()
            with b3:
                if can_edit and st.button("Cancel", key="cancel_" + t_key, type="secondary"):
                    r_del = requests.patch(f"{API}/tickets/{t_id}", json={"status":"resolved"})
                    if r_del.ok:
                        st.success("Ticket #" + t_key + " cancelled.")
                        st.rerun()

            if is_editing:
                with st.form("edit_form_" + t_key):
                    e_subj = st.text_input("Subject", value=t.get("subject", ""))
                    e_cat = st.selectbox("Category", ["general", "billing", "technical", "account"], index=["general", "billing", "technical", "account"].index(t.get("category", "general") if t.get("category", "general") in ["general", "billing", "technical", "account"] else "general"))
                    e_pri = st.selectbox("Priority", ["medium", "low", "high", "urgent"], index=["medium", "low", "high", "urgent"].index(t.get("priority", "medium") if t.get("priority", "medium") in ["medium", "low", "high", "urgent"] else "medium"))
                    e_msg = st.text_area("Message", value=tmsg(t), height=110)
                    if st.form_submit_button("💾 Save Changes", type="primary"):
                        requests.patch(f"{API}/tickets/{t_id}", json={"subject": e_subj, "priority": e_pri, "category": e_cat, "description": e_msg})
                        st.session_state.editing_ticket = None
                        st.success("Ticket updated!")
                        st.rerun()

            if response:
                with st.expander("💬 View AI Support Response"):
                    st.markdown('<div class="nd-response-box">' + h(response) + '</div>', unsafe_allow_html=True)
                    if t.get("status") == "resolved":
                        with st.form("fb_inline_" + t_key):
                            fb_r = st.slider("Rating", 1, 5, 5)
                            fb_msg = st.text_area("Comments", height=60)
                            if st.form_submit_button("Submit Feedback ⭐", type="primary"):
                                requests.post(f"{API}/feedback/", json={"ticket_id": t_id, "customer_id": cid, "rating": fb_r, "subject": "Ticket feedback", "message": fb_msg})
                                st.success("Thank you for your feedback! ⭐")
            elif t.get("status") == "open":
                st.markdown('<div class="nd-warn">⏳ Your ticket is waiting for the AI support response.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="nd-form-box"><div class="nd-panel-title">➕ Submit New Ticket</div><div class="nd-panel-sub">Describe the issue clearly for faster AI response.</div>', unsafe_allow_html=True)
        with st.form("new_ticket_form"):
            t_subj = st.text_input("Subject *", placeholder="Example: Refund not received after cancellation")
            t_cat = st.selectbox("Category", ["general", "billing", "technical", "account"])
            t_pri = st.selectbox("Priority", ["medium", "low", "high", "urgent"])
            t_msg = st.text_area("Describe your issue in detail *", height=145, placeholder="Include order ID, date, error message, or any important details...")
            if st.form_submit_button("Submit Ticket →", type="primary"):
                if not t_subj.strip() or not t_msg.strip():
                    st.error("Subject and message are required.")
                else:
                    r = requests.post(f"{API}/tickets/", json={"customer_id": cid, "customer_name": name, "customer_email": "", "subject": t_subj, "description": t_msg, "priority": t_pri, "category": t_cat})
                    if r.ok:
                        new_id = r.json().get("id") or r.json().get("ticket_id")
                        try:
                            requests.post(f"{API}/agent/generate/{new_id}", timeout=3)
                        except Exception:
                            pass
                        st.success("Ticket submitted successfully!")
                        st.rerun()
                    else:
                        st.error(r.text)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="nd-profile-card"><div style="display:flex;gap:1rem;align-items:center;margin-bottom:1rem;"><div class="nd-profile-avatar">' + h(initials) + '</div><div><div class="nd-panel-title">' + h(name) + '</div><div class="nd-panel-sub">Customer account</div></div></div><div class="nd-profile-row"><span class="nd-profile-label">Customer ID</span><span class="nd-profile-value">' + h(cid) + '</span></div><div class="nd-profile-row"><span class="nd-profile-label">Tickets</span><span class="nd-profile-value">' + str(total_n) + '</span></div><div class="nd-profile-row"><span class="nd-profile-label">Status</span><span class="nd-profile-value">Active</span></div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOMER — TICKET VIEW (full page read-only)
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "customer" and page == "ticket_view":
    sel = st.session_state.selected_ticket
    if not sel:
        st.session_state.current_page = "my_tickets"
        st.rerun()

    try:
        r = requests.get(f"{API}/tickets/{sel}", timeout=5)
        if not r.ok:
            st.error("Ticket not found.")
            st.stop()
        ticket = r.json()
    except Exception as e:
        st.error("Cannot connect to backend: " + str(e)); st.stop()

    if ticket.get("customer_id") != cid:
        st.markdown('<div class="nd-danger">🔒 Access denied.</div>', unsafe_allow_html=True)
        st.stop()

    if st.button("← Back to My Tickets", type="secondary"):
        st.session_state.current_page = "my_tickets"
        st.rerun()

    st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="nd-section-title">#' + str(tid(ticket)) + ' — ' +
                ticket.get("subject","") + '</div>', unsafe_allow_html=True)
    st.markdown('<div style="margin-bottom:1rem;">' + pill(ticket.get("status","open")) + '</div>',
                unsafe_allow_html=True)

    st.markdown('<div class="nd-card"><p style="font-size:12px;color:#5c6478;margin-bottom:0.5rem;">YOUR MESSAGE</p>'
                '<p style="font-size:14px;color:#c9cdd8;line-height:1.7;">' + tmsg(ticket) + '</p></div>',
                unsafe_allow_html=True)

    response = ticket.get("agent_final_response") or ticket.get("ai_draft_response")
    if response:
        st.markdown('<div class="nd-success">✅ Our support team has responded to your ticket.</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="nd-card"><p style="font-size:12px;color:#5c6478;margin-bottom:0.6rem;">SUPPORT RESPONSE</p>'
                    '<div class="nd-response-box">' + response + '</div></div>',
                    unsafe_allow_html=True)
        if ticket.get("status") == "resolved":
            st.divider()
            st.markdown("**How was your experience?**")
            with st.form("fb_view_" + str(sel)):
                rating = st.slider("Rating", 1, 5, 5)
                fb_msg = st.text_area("Comments (optional)", height=70)
                if st.form_submit_button("Submit Rating ⭐", type="primary"):
                    r2 = requests.post(f"{API}/feedback/", json={
                        "ticket_id": sel, "customer_id": cid,
                        "rating": rating, "subject": "Ticket feedback", "message": fb_msg
                    })
                    if r2.ok:
                        st.success("Thank you for your feedback! ⭐")
                    else:
                        st.error(r2.json().get("detail", r2.text))
    else:
        st.markdown('<div class="nd-warn">⏳ Our team is reviewing your request. Check back shortly.</div>',
                    unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOMER — PROFILE PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "customer" and page == "profile":
    all_tix = api_get("/tickets/", []) or []
    my_all = [t for t in all_tix if t.get("customer_id") == cid]
    all_fb = api_get("/feedback/", []) or []
    my_fb = [f for f in all_fb if f.get("customer_id") == cid]
    avg_rating = round(sum(f.get("rating", 0) for f in my_fb) / len(my_fb), 1) if my_fb else "—"

    open_count = sum(1 for t in my_all if t.get("status") == "open")
    resolved_count = sum(1 for t in my_all if t.get("status") == "resolved")
    latest_ticket = sorted(my_all, key=lambda x: tdate(x), reverse=True)[0] if my_all else None

    st.markdown(
        '<div class="nd-page-heading">'
        '<div><div class="nd-page-kicker">Customer Account</div>'
        '<div class="nd-section-title" style="font-size:26px;margin:0;">My Profile</div>'
        '<div class="nd-section-sub" style="margin:.35rem 0 0;">Clean overview of account details, tickets, and feedback activity.</div></div>'
        '<span class="nd-soft-chip">🟢 Active Customer</span>'
        '</div>', unsafe_allow_html=True
    )

    top_left, top_right = st.columns([0.85, 1.35])
    with top_left:
        st.markdown(
            '<div class="nd-profile-card" style="height:100%;">'
            '<div style="display:flex;gap:1rem;align-items:center;">'
            '<div class="nd-profile-avatar">' + h(initials) + '</div>'
            '<div><div style="font-size:22px;font-weight:800;color:#fff;letter-spacing:-.4px;">' + h(name) + '</div>'
            '<div class="nd-muted">Registered customer</div>'
            '<div style="margin-top:.7rem;"><span class="nd-soft-chip">Customer ID: ' + h(cid) + '</span></div>'
            '</div></div>'
            '<div class="nd-quick-box"><div class="nd-quick-icon">🤖</div><div><b style="color:#fff;">AI Support Enabled</b>'
            '<div class="nd-muted">Your tickets can be answered using knowledge base, memory, and automated AI response generation.</div></div></div>'
            '</div>', unsafe_allow_html=True
        )

    with top_right:
        st.markdown('<div class="nd-grid-card"><div class="nd-panel-title">Account Details</div>', unsafe_allow_html=True)
        rows = [
            ("Name", name),
            ("Customer ID", cid),
            ("Role", "Customer"),
            ("Account Status", "Active"),
            ("Support Mode", "Fully automated AI agent"),
        ]
        for label, value in rows:
            st.markdown(
                '<div class="nd-list-row"><span class="nd-profile-label">' + h(label) +
                '</span><span class="nd-profile-value">' + h(value) + '</span></div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    items = [
        ("Total Tickets", len(my_all), "All requests"),
        ("Open", open_count, "Needs response"),
        ("Resolved", resolved_count, "Completed"),
        ("Avg Rating", avg_rating, "Your feedback"),
    ]
    for col, (label, value, note) in zip([c1, c2, c3, c4], items):
        with col:
            st.markdown(
                '<div class="nd-stat-card"><div class="nd-stat-label">' + h(label) +
                '</div><div class="nd-stat-value">' + h(value) +
                '</div><div class="nd-stat-note">' + h(note) + '</div></div>',
                unsafe_allow_html=True
            )

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    activity_col, help_col = st.columns([1.25, .75])
    with activity_col:
        st.markdown('<div class="nd-panel"><div class="nd-panel-head"><div><div class="nd-panel-title">Recent Activity</div><div class="nd-panel-sub">Latest tickets connected to your account</div></div></div>', unsafe_allow_html=True)
        recent = sorted(my_all, key=lambda x: tdate(x), reverse=True)[:5]
        if not recent:
            st.markdown('<div class="nd-info">No ticket activity yet.</div>', unsafe_allow_html=True)
        for t in recent:
            st.markdown(
                '<div class="nd-ticket-pro"><div class="nd-ticket-top">'
                '<span class="nd-ticket-id">#' + h(tid(t)) + '</span>'
                '<span class="nd-ticket-title">' + h(t.get("subject", "—")) + '</span>' +
                pill(t.get("status", "open")) +
                '</div><div class="nd-ticket-foot"><span class="nd-mini">📅 ' + h(tdate(t) or "—") +
                '</span><span class="nd-mini">🏷 ' + h(t.get("category", "general")).title() +
                '</span><span class="nd-mini">⚡ ' + h(t.get("priority", "medium")).title() +
                '</span></div></div>', unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with help_col:
        last_text = "No ticket submitted yet."
        if latest_ticket:
            last_text = "#" + str(tid(latest_ticket)) + " · " + str(latest_ticket.get("subject", "—"))
        st.markdown(
            '<div class="nd-grid-card"><div class="nd-panel-title">Support Summary</div>'
            '<div class="nd-list-row"><span class="nd-profile-label">Last Ticket</span><span class="nd-profile-value">' + h(last_text) + '</span></div>'
            '<div class="nd-list-row"><span class="nd-profile-label">Feedback Given</span><span class="nd-profile-value">' + h(len(my_fb)) + '</span></div>'
            '<div class="nd-quick-box"><div class="nd-quick-icon">💡</div><div><b style="color:#fff;">Tip</b>'
            '<div class="nd-muted">When creating a ticket, include order ID, date, error message, and screenshots if available.</div></div></div>'
            '</div>', unsafe_allow_html=True
        )

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOMER — MY HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "customer" and page == "my_memory":
    st.markdown('<div class="nd-section-title">My Interaction History</div>', unsafe_allow_html=True)
    st.markdown('<div class="nd-section-sub">What our AI remembers from your past support interactions</div>',
                unsafe_allow_html=True)
    mem_data = api_get("/memory/" + (cid or ""), {})
    memories = mem_data.get("memories",[]) if isinstance(mem_data,dict) else []
    if not memories:
        st.markdown('<div class="nd-info">🧠 No interaction history yet. Resolve a ticket and it will appear here.</div>',
                    unsafe_allow_html=True)
    else:
        st.success("Found " + str(len(memories)) + " stored interactions")
        for i,m in enumerate(memories,1):
            with st.expander("Interaction " + str(i) + " · " + m.get('created_at','')[:10]):
                st.write(m.get("memory",""))

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOMER — GIVE FEEDBACK
# ═══════════════════════════════════════════════════════════════════════════════
elif role == "customer" and page == "my_feedback":
    st.markdown('<div class="nd-section-title">Give Feedback</div>', unsafe_allow_html=True)
    st.markdown('<div class="nd-section-sub">Rate your support experience</div>', unsafe_allow_html=True)
    all_tix  = api_get("/tickets/", []) or []
    resolved = [t for t in all_tix if t.get("customer_id") == cid and t.get("status") == "resolved"]
    if not resolved:
        st.markdown('<div class="nd-info">⭐ No resolved tickets yet. Feedback can be submitted once a ticket is resolved.</div>',
                    unsafe_allow_html=True)
    else:
        options = {"Ticket #" + str(tid(t)) + " — " + t['subject']: tid(t) for t in resolved}
        chosen  = st.selectbox("Select resolved ticket", list(options.keys()))
        sel_tid = options[chosen]
        with st.form("customer_fb_form"):
            rating  = st.slider("How satisfied were you?", 1, 5, 5)
            st.markdown('<p style="font-size:20px;margin:-0.3rem 0 0.5rem;">' + "⭐" * 3 + '</p>',
                        unsafe_allow_html=True)
            fb_subj = st.text_input("Subject", placeholder="e.g. Issue resolved quickly!")
            fb_msg  = st.text_area("Tell us more (optional)", height=80)
            if st.form_submit_button("Submit Feedback ⭐", type="primary"):
                r = requests.post(f"{API}/feedback/", json={
                    "ticket_id": sel_tid, "customer_id": cid,
                    "rating": rating, "subject": fb_subj or "Ticket feedback", "message": fb_msg
                })
                if r.ok:
                    st.success("Thank you! " + "⭐" * rating)
                else:
                    st.error(r.json().get("detail", r.text))
    st.divider()
    st.markdown("**Your previous feedback:**")
    all_fb = api_get("/feedback/", []) or []
    my_fb  = [f for f in all_fb if f.get("customer_id") == cid]
    if not my_fb:
        st.info("No feedback submitted yet.")
    for fb in my_fb:
        stars = "⭐" * fb["rating"]
        card = ('<div class="nd-card" style="padding:0.7rem 1.1rem;">'
                + stars + ' — <b style="color:#c9cdd8;">Ticket #' + str(fb['ticket_id']) + '</b> — '
                '<span style="color:#5c6478;font-size:12px;">' + fb['created_at'][:10] + '</span>'
                '</div>')
        st.markdown(card, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════
else:
    first = ADMIN_NAV[0][0] if role == "admin" else CUSTOMER_NAV[0][0]
    st.session_state.current_page = first
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)