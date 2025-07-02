import sqlite3
from flask import Flask, render_template_string, request, redirect
from collections import defaultdict

app = Flask(__name__)
DB_NAME = 'inventory.db'

# DB 초기화
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            sku TEXT NOT NULL,
            option TEXT,
            location TEXT DEFAULT '본사',
            inbound INTEGER DEFAULT 0,
            outbound INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 현재고 계산
def get_inventory():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, product_name, sku, option, location, inbound, outbound, (inbound - outbound) as current_stock FROM inventory")
    rows = c.fetchall()
    conn.close()
    return rows

# SKU별 위치 구분 재고 요약
def get_inventory_summary():
    inventory = get_inventory()
    summary = defaultdict(lambda: {'본사': 0, '3PL': 0, 'info': {}})
    for row in inventory:
        _, name, sku, option, location, _, _, stock = row
        key = (sku, option)
        summary[key]['info'] = {'product_name': name, 'sku': sku, 'option': option}
        summary[key][location] += stock
    return summary

# HTML 템플릿
template = '''
<!doctype html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>재고관리 시스템</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>#addForm { display: none; }</style>
    <script>
        function toggleAddForm() {
            const form = document.getElementById('addForm');
            form.style.display = form.style.display === 'none' ? 'block' : 'none';
        }
        function toggleDeleteButton() {
            const selected = document.querySelectorAll('input[name="delete_skus"]:checked');
            document.getElementById('delete-selected-btn').style.display = selected.length > 0 ? 'inline-block' : 'none';
        }
    </script>
</head>
<body>
<div class="container mt-5">
    <h2 class="mb-4">📥 입고 / 출고 등록</h2>
    <form method="post" action="/update" class="row g-3 mb-5">
        <div class="col-md-3">
            <label class="form-label">SKU</label>
            <input type="text" name="sku" class="form-control" placeholder="SKU" required>
        </div>
        <div class="col-md-2">
            <label class="form-label">입고 수량</label>
            <input type="number" name="inbound" class="form-control" placeholder="입고" value="0">
        </div>
        <div class="col-md-2">
            <label class="form-label">출고 수량</label>
            <input type="number" name="outbound" class="form-control" placeholder="출고" value="0">
        </div>
        <div class="col-md-3">
            <label class="form-label">위치</label>
            <select name="location" class="form-select">
                <option value="본사">본사</option>
                <option value="3PL">3PL</option>
            </select>
        </div>
        <div class="col-md-2 d-flex align-items-end">
            <button type="submit" class="btn btn-success w-100">업데이트</button>
        </div>
    </form>

    <div class="text-end mb-3">
        <button class="btn btn-outline-primary" onclick="toggleAddForm()">➕ 상품 추가</button>
    </div>

    <div id="addForm" class="bg-light p-4 rounded mb-4">
        <h4 class="mb-3">상품 추가</h4>
        <form method="post" action="/add" class="row g-3">
            <div class="col-md-4">
                <input type="text" name="product_name" class="form-control" placeholder="상품명" required>
            </div>
            <div class="col-md-4">
                <input type="text" name="sku" class="form-control" placeholder="SKU" required>
            </div>
            <div class="col-md-4">
                <input type="text" name="option" class="form-control" placeholder="옵션">
            </div>
            <div class="col-md-12 d-flex justify-content-end gap-2">
                <button type="submit" class="btn btn-primary">추가</button>
                <button type="button" class="btn btn-secondary" onclick="toggleAddForm()">취소</button>
            </div>
        </form>
    </div>

    <h2 class="mb-3">📦 가구 재고 리스트</h2>
    <form method="post" action="/delete-selected">
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead class="table-light">
                    <tr>
                        <th><input type="checkbox" onclick="document.querySelectorAll('input[name=delete_skus]').forEach(cb => cb.checked = this.checked); toggleDeleteButton();"></th>
                        <th>상품명</th>
                        <th>SKU</th>
                        <th>옵션</th>
                        <th>본사 재고</th>
                        <th>3PL 재고</th>
                        <th>총 재고</th>
                    </tr>
                </thead>
                <tbody>
                    {% for key, val in summary.items() %}
                    <tr>
                        <td><input type="checkbox" name="delete_skus" value="{{ val.info.sku }}||{{ val.info.option }}" onclick="toggleDeleteButton()"></td>
                        <td>{{ val.info.product_name }}</td>
                        <td>{{ val.info.sku }}</td>
                        <td>{{ val.info.option }}</td>
                        <td class="text-end">{{ val['본사'] }}</td>
                        <td class="text-end">{{ val['3PL'] }}</td>
                        <td class="text-end fw-bold">{{ val['본사'] + val['3PL'] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <div class="text-end">
            <button type="submit" id="delete-selected-btn" class="btn btn-danger" style="display:none;">선택 삭제</button>
        </div>
    </form>
</div>
</body>
</html>
'''

@app.route('/')
def index():
    summary = get_inventory_summary()
    rows = get_inventory()
    return render_template_string(template, rows=rows, summary=summary)

@app.route('/add', methods=['POST'])
def add_product():
    product_name = request.form['product_name']
    sku = request.form['sku']
    option = request.form.get('option', '')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO inventory (product_name, sku, option, location) VALUES (?, ?, ?, '본사')", (product_name, sku, option))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/update', methods=['POST'])
def update_stock():
    sku = request.form['sku']
    inbound = int(request.form['inbound'])
    outbound = int(request.form['outbound'])
    location = request.form.get('location', '본사')

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # SKU + location 존재 여부 확인
    c.execute("SELECT COUNT(*) FROM inventory WHERE sku = ? AND location = ?", (sku, location))
    exists = c.fetchone()[0]

    if exists:
        c.execute("UPDATE inventory SET inbound = inbound + ?, outbound = outbound + ? WHERE sku = ? AND location = ?",
                  (inbound, outbound, sku, location))
    else:
        # 기존 product_name과 option 가져오기
        c.execute("SELECT product_name, option FROM inventory WHERE sku = ? LIMIT 1", (sku,))
        result = c.fetchone()
        if result:
            product_name, option = result
        else:
            product_name, option = sku, ''

        c.execute("INSERT INTO inventory (product_name, sku, option, location, inbound, outbound) VALUES (?, ?, ?, ?, ?, ?)",
                  (product_name, sku, option, location, inbound, outbound))

    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete-selected', methods=['POST'])
def delete_selected():
    sku_options = request.form.getlist('delete_skus')
    if sku_options:
        split_keys = [tuple(s.split('||')) for s in sku_options]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        for sku, option in split_keys:
            c.execute("DELETE FROM inventory WHERE sku = ? AND option = ?", (sku, option))
        conn.commit()
        conn.close()
    return redirect('/')

init_db()
app.run(debug=True, port=5000)
