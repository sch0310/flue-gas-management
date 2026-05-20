#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
烟气运维标气管理系统
作者: 孙朝辉
功能: 现在运维标气管理
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string, redirect, url_for, jsonify, flash
from flask_cors import CORS

DB_PATH = 'flue_gas.db'
CONFIG_PATH = 'config.json'

# ============================================================
# 工厂与标气配置
# ============================================================
FACTORIES = {
    "新格有色金属": ["二氧化硫", "一氧化氮", "氧", "高纯氮"],
    "华鼎铜业": ["二氧化硫", "一氧化氮", "氧", "高纯氮"],
    "北方常铝": ["二氧化硫", "一氧化氮","甲烷", "氧", "高纯氮"],
    "还原铁入口": ["二氧化硫", "一氧化氮", "氧", "高纯氮"],
    "还原铁出口": ["二氧化硫", "一氧化氮", "二氧化氮", "氧", "高纯氮"],
    "绿源危废": ["二氧化硫", "一氧化氮", "二氧化氮", "一氧化碳", "氯化氢", "氧", "高纯氮"],
}

# ============================================================
# 配置管理
# ============================================================
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'serverchan_send_key': ''}

def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# ============================================================
# 数据库初始化
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS gas_standards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factory TEXT NOT NULL,
            gas_name TEXT NOT NULL,
            concentration REAL NOT NULL,
            production_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            reminder_sent INTEGER DEFAULT 0
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_expiry ON gas_standards(expiry_date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_factory ON gas_standards(factory)')
    conn.commit()
    conn.close()

# ============================================================
# Flask 应用
# ============================================================
app = Flask(__name__)
app.secret_key = 'flue_gas_management_2026'
CORS(app)

@app.route('/')
def index():
    """首页 - 显示所有标气记录"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, factory, gas_name, concentration, production_date, expiry_date, reminder_sent
        FROM gas_standards
        ORDER BY expiry_date ASC
    ''')
    rows = c.fetchall()
    conn.close()

    today = datetime.now().date()
    records = []
    for row in rows:
        expiry = datetime.strptime(row[5], '%Y-%m-%d').date()
        days_left = (expiry - today).days
        status = '正常'
        if days_left < 0:
            status = '已过期'
        elif days_left <= 45:
            status = '即将到期'
        records.append({
            'id': row[0],
            'factory': row[1],
            'gas_name': row[2],
            'concentration': row[3],
            'production_date': row[4],
            'expiry_date': row[5],
            'days_left': days_left,
            'status': status,
            'reminder_sent': row[6]
        })

    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>标气管理 - 首页</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f7fa; color: #333; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
            .header h1 { font-size: 1.5rem; }
            .header p { font-size: 0.9rem; opacity: 0.9; margin-top: 5px; }
            .container { max-width: 900px; margin: 20px auto; padding: 0 15px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .stat-card { background: white; border-radius: 10px; padding: 15px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .stat-card .num { font-size: 2rem; font-weight: bold; color: #667eea; }
            .stat-card .label { font-size: 0.85rem; color: #888; margin-top: 5px; }
            .btn-group { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
            .btn { display: block; padding: 15px 20px; border-radius: 10px; text-decoration: none; font-weight: 500; cursor: pointer; border: none; font-size: 1rem; text-align: center; }
            .btn-primary { background: #667eea; color: white; }
            .btn-success { background: #52c41a; color: white; }
            .btn-warning { background: #faad14; color: #333; }
            .btn-danger { background: #ff4d4f; color: white; }
            .btn:hover { opacity: 0.9; }
            .filter-bar { background: white; border-radius: 10px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
            .filter-bar select { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9rem; }
            table { width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-collapse: collapse; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #f0f0f0; }
            th { background: #fafafa; font-weight: 600; font-size: 0.85rem; color: #666; }
            tr:hover { background: #f9f9f9; }
            .badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
            .badge-normal { background: #e6fffb; color: #13c2c2; }
            .badge-warning { background: #fff7e6; color: #fa8c16; }
            .badge-danger { background: #fff1f0; color: #ff4d4f; }
            .empty { text-align: center; padding: 40px; color: #999; }
            .actions { display: flex; gap: 5px; }
            .actions button { padding: 4px 8px; font-size: 0.75rem; border-radius: 4px; border: 1px solid #ddd; background: white; cursor: pointer; }
            .actions button:hover { background: #f0f0f0; }
            @media (max-width: 600px) {
                table { font-size: 0.85rem; }
                th, td { padding: 8px 10px; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏭 烟气运维标气管理系统</h1>
            <p>6个现场标气统一管理 · 到期前45天自动提醒</p>
        </div>
        <div class="container">
            <div class="stats">
                <div class="stat-card"><div class="num">{{ total }}</div><div class="label">标气总数</div></div>
                <div class="stat-card"><div class="num">{{ normal }}</div><div class="label">正常</div></div>
                <div class="stat-card"><div class="num">{{ warning }}</div><div class="label">即将到期</div></div>
                <div class="stat-card"><div class="num">{{ expired }}</div><div class="label">已过期</div></div>
            </div>
            <div class="btn-group">
                <a href="/form" class="btn btn-primary" style="display:block; margin-bottom:10px; text-align:center;">➕ 新增标气</a>
                <a href="/qrcode" class="btn btn-success" style="display:block; margin-bottom:10px; text-align:center;">📱 分享链接</a>
                <a href="/check" class="btn btn-warning" style="display:block; margin-bottom:10px; text-align:center;">🔔 检查提醒</a>
                <a href="/config" class="btn btn-danger" style="display:block; margin-bottom:10px; text-align:center;">⚙️ 配置</a>
            </div>
            <div class="filter-bar">
                <label>工厂筛选：</label>
                <select onchange="filterTable()">
                    <option value="">全部</option>
                    {% for f in factories.keys() %}
                    <option value="{{ f }}">{{ f }}</option>
                    {% endfor %}
                </select>
                <label>状态筛选：</label>
                <select onchange="filterTable()">
                    <option value="">全部</option>
                    <option value="正常">正常</option>
                    <option value="即将到期">即将到期</option>
                    <option value="已过期">已过期</option>
                </select>
            </div>
            {% if records %}
            <table id="recordTable">
                <thead>
                    <tr>
                        <th>工厂</th>
                        <th>标气</th>
                        <th>浓度</th>
                        <th>生产日期</th>
                        <th>到期日期</th>
                        <th>剩余天数</th>
                        <th>状态</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in records %}
                    <tr data-factory="{{ r.factory }}" data-status="{{ r.status }}">
                        <td>{{ r.factory }}</td>
                        <td>{{ r.gas_name }}</td>
                        <td>{{ "%.2f"|format(r.concentration) }}</td>
                        <td>{{ r.production_date }}</td>
                        <td>{{ r.expiry_date }}</td>
                        <td>{% if r.days_left >= 0 %}{{ r.days_left }}天{% else %}已过期{{ -r.days_left }}天{% endif %}</td>
                        <td><span class="badge badge-{% if r.status == '正常' %}normal{% elif r.status == '即将到期' %}warning{% else %}danger{% endif %}">{{ r.status }}</span></td>
                        <td class="actions">
                            <button onclick="deleteRecord({{ r.id }})">删除</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="empty">
                <p>📭 暂无标气记录</p>
                <p style="margin-top:10px;"><a href="/form" style="color:#667eea;">点击这里新增第一条记录</a></p>
            </div>
            {% endif %}
        </div>
        <script>
            function filterTable() {
                const factorySelect = document.querySelectorAll('.filter-bar select')[0];
                const statusSelect = document.querySelectorAll('.filter-bar select')[1];
                const factoryVal = factorySelect.value;
                const statusVal = statusSelect.value;
                const rows = document.querySelectorAll('#recordTable tbody tr');
                rows.forEach(row => {
                    const showFactory = !factoryVal || row.dataset.factory === factoryVal;
                    const showStatus = !statusVal || row.dataset.status === statusVal;
                    row.style.display = (showFactory && showStatus) ? '' : 'none';
                });
            }
            function deleteRecord(id) {
                if (confirm('确认删除这条记录？')) {
                    fetch('/api/delete/' + id, {method: 'POST'}).then(() => location.reload());
                }
            }
        </script>
    </body>
    </html>
    '''
    total = len(records)
    normal = sum(1 for r in records if r['status'] == '正常')
    warning = sum(1 for r in records if r['status'] == '即将到期')
    expired = sum(1 for r in records if r['status'] == '已过期')
    return render_template_string(html, records=records, total=total, normal=normal, warning=warning, expired=expired, factories=FACTORIES)

@app.route('/form')
def form():
    """填写标气信息表单"""
    factories_json = json.dumps(FACTORIES, ensure_ascii=False)
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>新增标气记录</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f7fa; color: #333; padding: 20px; }
            .container { max-width: 500px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #667eea; font-size: 1.5rem; }
            .form-card { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 8px; font-weight: 500; color: #555; }
            .form-group select, .form-group input {
                width: 100%; padding: 12px 15px; border: 2px solid #e8e8e8;
                border-radius: 10px; font-size: 1rem; transition: border-color 0.3s;
                background: white; appearance: none; -webkit-appearance: none;
            }
            .form-group select { background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 15px center; }
            .form-group input:focus, .form-group select:focus { outline: none; border-color: #667eea; }
            .btn-submit { width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 10px; font-size: 1.1rem; font-weight: 600; cursor: pointer; margin-top: 10px; }
            .btn-submit:active { transform: scale(0.98); }
            .btn-back { display: block; text-align: center; margin-top: 15px; color: #667eea; text-decoration: none; }
            .toast { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #52c41a; color: white; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; display: none; }
            .concentration-unit { color: #999; font-size: 0.85rem; margin-left: 5px; }
        </style>
    </head>
    <body>
        <div class="toast" id="toast"></div>
        <div class="container">
            <div class="header">
                <h1>📝 新增标气记录</h1>
                <p style="color:#999;margin-top:5px;">请填写标气信息</p>
            </div>
            <div class="form-card">
                <form id="gasForm">
                    <div class="form-group">
                        <label>🏭 选择工厂</label>
                        <select id="factory" name="factory" required onchange="updateGasOptions()">
                            <option value="">-- 请选择工厂 --</option>
                            {% for f in factories.keys() %}
                            <option value="{{ f }}">{{ f }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>🧪 选择标气</label>
                        <select id="gas_name" name="gas_name" required>
                            <option value="">-- 请先选择工厂 --</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>📊 标气浓度 <span class="concentration-unit">(μmol/mol，保留2位小数)</span></label>
                        <input type="number" step="0.01" name="concentration" placeholder="例如：50.00" required>
                    </div>
                    <div class="form-group">
                        <label>📅 生产日期</label>
                        <input type="date" name="production_date" required>
                    </div>
                    <button type="submit" class="btn-submit">✅ 提交保存</button>
                </form>
            </div>
            <a href="/" class="btn-back">← 返回首页</a>
        </div>
        <script>
            const FACTORIES = ''' + factories_json + ''';

            function updateGasOptions() {
                const factory = document.getElementById('factory').value;
                const gasSelect = document.getElementById('gas_name');
                gasSelect.innerHTML = '<option value="">-- 请选择标气 --</option>';
                if (factory && FACTORIES[factory]) {
                    FACTORIES[factory].forEach(gas => {
                        const opt = document.createElement('option');
                        opt.value = gas;
                        opt.textContent = gas;
                        gasSelect.appendChild(opt);
                    });
                } else {
                    gasSelect.innerHTML = '<option value="">-- 请先选择工厂 --</option>';
                }
            }

            document.getElementById('gasForm').addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                const data = Object.fromEntries(formData);

                // 验证浓度小数位数
                const conc = parseFloat(data.concentration);
                if (isNaN(conc) || conc < 0) {
                    showToast('请输入有效的浓度值', 'error');
                    return;
                }

                fetch('/api/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                })
                .then(res => res.json())
                .then(result => {
                    if (result.success) {
                        showToast('✅ 保存成功！');
                        setTimeout(() => window.location.href = '/', 1500);
                    } else {
                        showToast('❌ ' + result.message, 'error');
                    }
                });
            });

            function showToast(msg, type='success') {
                const toast = document.getElementById('toast');
                toast.textContent = msg;
                toast.style.background = type === 'error' ? '#ff4d4f' : '#52c41a';
                toast.style.display = 'block';
                setTimeout(() => toast.style.display = 'none', 3000);
            }

            // 默认今天日期
            document.querySelector('input[name="production_date"]').value = new Date().toISOString().split('T')[0];
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, factories=FACTORIES)

@app.route('/config', methods=['GET', 'POST'])
def config_page():
    """配置页面"""
    if request.method == 'POST':
        send_key = request.form.get('send_key', '').strip()
        config = load_config()
        config['serverchan_send_key'] = send_key
        save_config(config)
        return redirect('/config?success=1')

    config = load_config()
    success = request.args.get('success')
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>系统配置</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f7fa; padding: 20px; }
            .container { max-width: 500px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #667eea; }
            .config-card { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 8px; font-weight: 500; color: #555; }
            .form-group input { width: 100%; padding: 12px 15px; border: 2px solid #e8e8e8; border-radius: 10px; font-size: 1rem; }
            .form-group input:focus { outline: none; border-color: #667eea; }
            .form-group .hint { font-size: 0.85rem; color: #999; margin-top: 5px; }
            .btn-submit { width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 10px; font-size: 1.1rem; font-weight: 600; cursor: pointer; }
            .btn-back { display: block; text-align: center; margin-top: 15px; color: #667eea; text-decoration: none; }
            .alert { padding: 12px; border-radius: 8px; margin-bottom: 20px; text-align: center; }
            .alert-success { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚙️ 系统配置</h1>
            </div>
            {% if success %}
            <div class="alert alert-success">✅ 配置保存成功！</div>
            {% endif %}
            <div class="config-card">
                <form method="POST">
                    <div class="form-group">
                        <label>🔔 Server酱 SendKey</label>
                        <input type="text" name="send_key" value="{{ config.serverchan_send_key }}" placeholder="请输入Server酱SendKey">
                        <div class="hint">用于微信提醒推送。获取方式：访问 <a href="https://sct.ftqq.com" target="_blank">sct.ftqq.com</a> 注册并获取SendKey</div>
                    </div>
                    <button type="submit" class="btn-submit">💾 保存配置</button>
                </form>
            </div>
            <a href="/" class="btn-back">← 返回首页</a>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, config=config, success=success)

@app.route('/qrcode')
def qrcode_page():
    """显示链接分享页面"""
    form_url = request.host_url.rstrip('/') + '/form'

    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>链接分享 - 标气管理</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f7fa; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }
            .card { background: white; border-radius: 20px; padding: 40px; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.1); max-width: 400px; width: 100%; }
            .card h1 { color: #667eea; font-size: 1.3rem; margin-bottom: 10px; }
            .card p { color: #999; font-size: 0.9rem; margin-bottom: 30px; }
            .url-box { background: #f5f7fa; border-radius: 8px; padding: 15px; font-size: 0.85rem; color: #667eea; word-break: break-all; margin-bottom: 20px; font-weight: 500; }
            .btn { display: block; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: 500; margin-bottom: 10px; }
            .btn-primary { background: #667eea; color: white; }
            .btn-success { background: #52c41a; color: white; border: none; cursor: pointer; font-size: 1rem; }
            .btn-back { display: inline-block; padding: 10px 20px; background: #999; color: white; text-decoration: none; border-radius: 8px; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>📱 分享标气录入链接</h1>
            <p>复制下方链接或点击直接打开</p>
            <div class="url-box">''' + form_url + '''</div>
            <button class="btn btn-success" onclick="copyUrl()">📋 复制链接</button>
            <a href="''' + form_url + '''" class="btn btn-primary">🔗 直接打开</a>
            <a href="/" class="btn-back">← 返回首页</a>
        </div>
        <script>
            function copyUrl() {
                navigator.clipboard.writeText("''' + form_url + '''").then(() => alert("链接已复制！"));
            }
        </script>
    </body>
    </html>
    '''
    return html

@app.route('/api/add', methods=['POST'])
def api_add():
    """API: 新增标气记录"""
    data = request.json
    factory = data.get('factory')
    gas_name = data.get('gas_name')
    concentration = data.get('concentration')
    production_date = data.get('production_date')

    if not all([factory, gas_name, concentration, production_date]):
        return jsonify({'success': False, 'message': '请填写完整信息'})

    try:
        concentration = float(concentration)
    except:
        return jsonify({'success': False, 'message': '浓度格式错误'})

    # 计算到期日期（生产日期 + 365天）
    prod_date = datetime.strptime(production_date, '%Y-%m-%d')
    expiry_date = prod_date + timedelta(days=365)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO gas_standards (factory, gas_name, concentration, production_date, expiry_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (factory, gas_name, concentration, production_date, expiry_date.strftime('%Y-%m-%d'), datetime.now().isoformat()))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/delete/<int:record_id>', methods=['POST'])
def api_delete(record_id):
    """API: 删除记录"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM gas_standards WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/check')
def check_reminders():
    """检查并发送提醒（支持GET/POST）"""
    config = load_config()
    send_key = config.get('serverchan_send_key', '')

    if not send_key:
        # 未配置，显示配置提示页面
        html = '''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>检查提醒</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f7fa; padding: 20px; }
                .container { max-width: 600px; margin: 50px auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
                h1 { color: #ff4d4f; margin-bottom: 20px; }
                .hint { color: #999; line-height: 1.6; }
                .btn { display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚠️ 未配置 Server酱 SendKey</h1>
                <p class="hint">请先进入"配置"页面，填写 Server酱 SendKey，才能发送微信提醒。</p>
                <p class="hint" style="margin-top:15px;">获取方式：访问 <a href="https://sct.ftqq.com" target="_blank">sct.ftqq.com</a> 注册并获取 SendKey</p>
                <a href="/config" class="btn">前往配置 →</a>
            </div>
        </body>
        </html>
        '''
        return html

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, factory, gas_name, concentration, production_date, expiry_date
        FROM gas_standards
        WHERE reminder_sent = 0
    ''')
    rows = c.fetchall()
    conn.close()

    today = datetime.now().date()
    reminders = []

    for row in rows:
        expiry = datetime.strptime(row[5], '%Y-%m-%d').date()
        days_left = (expiry - today).days
        if 0 <= days_left <= 45:
            reminders.append({
                'id': row[0],
                'factory': row[1],
                'gas_name': row[2],
                'concentration': row[3],
                'production_date': row[4],
                'expiry_date': row[5],
                'days_left': days_left
            })

    # 发送微信提醒
    sent_count = 0
    failed_count = 0
    for r in reminders:
        title = f"⚠️ 标气即将到期提醒"
        content = f"""
## 标气到期提醒

- **工厂**: {r['factory']}
- **标气**: {r['gas_name']}
- **浓度**: {r['concentration']} μmol/mol
- **生产日期**: {r['production_date']}
- **到期日期**: {r['expiry_date']}
- **剩余天数**: **{r['days_left']}天**

请及时采购新标气！
        """
        try:
            import requests
            url = f"https://sctapi.ftqq.com/{send_key}.send"
            resp = requests.post(url, data={'title': title, 'desp': content}, timeout=10)
            if resp.json().get('code') == 0:
                # 标记已发送
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute('UPDATE gas_standards SET reminder_sent = 1 WHERE id = ?', (r['id'],))
                conn.commit()
                conn.close()
                sent_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"发送失败: {e}")
            failed_count += 1

    # 显示结果页面
    html = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>检查提醒结果</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f7fa; padding: 20px; }
            .container { max-width: 600px; margin: 50px auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            h1 { color: #667eea; margin-bottom: 20px; }
            .result-item { padding: 15px; background: #f9f9f9; border-radius: 8px; margin-bottom: 10px; }
            .result-item .label { color: #999; font-size: 0.9rem; }
            .result-item .value { font-size: 1.2rem; font-weight: bold; color: #333; }
            .btn { display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; margin-top: 20px; }
            .stats { display: flex; gap: 15px; margin-bottom: 20px; }
            .stat { flex: 1; text-align: center; padding: 15px; background: #f9f9f9; border-radius: 8px; }
            .stat .num { font-size: 1.5rem; font-weight: bold; }
            .stat .label { font-size: 0.85rem; color: #999; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔔 检查提醒结果</h1>
            <div class="stats">
                <div class="stat">
                    <div class="num">{{ checked }}</div>
                    <div class="label">检查记录数</div>
                </div>
                <div class="stat">
                    <div class="num">{{ reminders }}</div>
                    <div class="label">即将到期</div>
                </div>
                <div class="stat">
                    <div class="num">{{ sent }}</div>
                    <div class="label">已发送提醒</div>
                </div>
            </div>
            {% if reminders_list %}
            <h3 style="margin-bottom:15px;color:#fa8c16;">⚠️ 即将到期的标气</h3>
            {% for r in reminders_list %}
            <div class="result-item">
                <div class="label">工厂</div>
                <div class="value">{{ r.factory }}</div>
                <div class="label" style="margin-top:10px;">标气</div>
                <div class="value">{{ r.gas_name }} ({{ r.concentration }} μmol/mol)</div>
                <div class="label" style="margin-top:10px;">到期日期</div>
                <div class="value">{{ r.expiry_date }} (剩余 {{ r.days_left }} 天)</div>
            </div>
            {% endfor %}
            {% else %}
            <p style="color:#52c41a;font-size:1.1rem;">✅ 没有即将到期的标气，一切正常！</p>
            {% endif %}
            <a href="/" class="btn">← 返回首页</a>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, checked=len(rows), reminders=len(reminders), sent=sent_count, reminders_list=reminders)

@app.route('/api/records')
def api_records():
    """API: 获取所有记录"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM gas_standards ORDER BY expiry_date ASC')
    rows = c.fetchall()
    conn.close()
    columns = ['id', 'factory', 'gas_name', 'concentration', 'production_date', 'expiry_date', 'created_at', 'reminder_sent']
    result = [dict(zip(columns, row)) for row in rows]
    return jsonify(result)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
