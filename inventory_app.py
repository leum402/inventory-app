import os
from flask import Flask, render_template_string, request, redirect
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict

app = Flask(__name__)

# Render PostgreSQL 연결 주소
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://inventory_user:8mdkay8gO99mIr4hOyKaI80OoUxBNguG@dpg-d1n04pvdiees73ehph90-a/inventory_oqde'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 📦 테이블 정의
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(120), nullable=False)
    sku = db.Column(db.String(80), nullable=False)
    option = db.Column(db.String(120), nullable=True)
    location = db.Column(db.String(20), default='본사')
    inbound = db.Column(db.Integer, default=0)
    outbound = db.Column(db.Integer, default=0)

    @property
    def current_stock(self):
        return self.inbound - self.outbound

# 📊 요약 계산
def get_inventory_summary():
    all_items = Inventory.query.all()
    summary = defaultdict(lambda: {'본사': 0, '3PL': 0, 'info': {}})
    for item in all_items:
        key = (item.sku, item.option or '')
        summary[key]['info'] = {'product_name': item.product_name, 'sku': item.sku, 'option': item.option or ''}
        summary[key][item.location] += item.current_stock
    return summary

# 🖼️ HTML 템플릿 (Jinja2)
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
            const selected = document.querySelectorAll('input[name=\"delete_skus\"]:checked');
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
            <input type="text" name="sku" class="form-control" required>
        </div>
        <div class="col-md-2">
            <label class="form-label">입고 수량</label>
            <input type="number" name="inbound" class="form-control" value="0">
        </div>
        <div class="col-md-2">
            <label class="form-label">출고 수량</label>
            <input type="number" name="outbound" class="form-control" value="0">
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
    return render_template_string(template, summary=summary)

@app.route('/add', methods=['POST'])
def add_product():
    product_name = request.form['product_name']
    sku = request.form['sku']
    option = request.form.get('option', '')
    new_item = Inventory(product_name=product_name, sku=sku, option=option, location='본사')
    db.session.add(new_item)
    db.session.commit()
    return redirect('/')

@app.route('/update', methods=['POST'])
def update_stock():
    sku = request.form['sku']
    inbound = int(request.form['inbound'])
    outbound = int(request.form['outbound'])
    location = request.form.get('location', '본사')

    item = Inventory.query.filter_by(sku=sku, location=location).first()
    if item:
        item.inbound += inbound
        item.outbound += outbound
    else:
        # 이름과 옵션은 해당 SKU의 기존 데이터에서 가져옴
        fallback = Inventory.query.filter_by(sku=sku).first()
        product_name = fallback.product_name if fallback else sku
        option = fallback.option if fallback else ''
        item = Inventory(product_name=product_name, sku=sku, option=option, location=location,
                         inbound=inbound, outbound=outbound)
        db.session.add(item)
    db.session.commit()
    return redirect('/')

@app.route('/delete-selected', methods=['POST'])
def delete_selected():
    sku_options = request.form.getlist('delete_skus')
    for pair in sku_options:
        sku, option = pair.split('||')
        items = Inventory.query.filter_by(sku=sku, option=option).all()
        for item in items:
            db.session.delete(item)
    db.session.commit()
    return redirect('/')

# 포트 바인딩 (for Render)
if __name__ == "__main__":
    db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
