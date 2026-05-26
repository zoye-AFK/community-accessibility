from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import time
import math
from functools import lru_cache

app = Flask(__name__)
CORS(app)

AMAP_KEY = "bd550f9f173219720895ca60459e774f"  # 请替换成您的高德Key！

# 预设社区（作为快捷选项）
PRESET_COMMUNITIES = [
    {"name": "佛山禅城区祖庙街道社区", "city": "佛山", "address": "广东省佛山市禅城区祖庙路", "lat": 23.032846, "lon": 113.119940},
    {"name": "佛山禅城区石湾镇街道社区", "city": "佛山", "address": "广东省佛山市禅城区镇中路", "lat": 22.998236, "lon": 113.109719},
    {"name": "佛山南海区桂城街道社区", "city": "佛山", "address": "广东省佛山市南海区桂城街道", "lat": 23.037979, "lon": 113.161502},
    {"name": "中山石岐街道社区", "city": "中山", "address": "广东省中山市石岐区中山路", "lat": 22.536514, "lon": 113.388277},
    {"name": "中山东区街道社区", "city": "中山", "address": "广东省中山市东区街道", "lat": 22.516493, "lon": 113.399189},
    {"name": "珠海香洲区拱北街道社区", "city": "珠海", "address": "广东省珠海市香洲区拱北口岸", "lat": 22.271644, "lon": 113.576892},
    {"name": "珠海香洲区吉大街道社区", "city": "珠海", "address": "广东省珠海市香洲区吉大景山路", "lat": 22.247878, "lon": 113.575937},
]

# 8大类设施分类
FACILITY_CATEGORIES = {
    "1-小学": {"keywords": "小学", "icon": "🏫", "color": "#28a745"},
    "2-中学": {"keywords": "中学|初中|高中", "icon": "🏫", "color": "#28a745"},
    "3-幼儿园": {"keywords": "幼儿园|托儿所", "icon": "🏫", "color": "#28a745"},
    "4-大学": {"keywords": "大学|学院|高校", "icon": "🏫", "color": "#28a745"},
    "5-医疗卫生": {"keywords": "医院|门诊|诊所|卫生站|护理院", "icon": "🏥", "color": "#dc3545"},
    "6-文化体育": {"keywords": "图书馆|博物馆|体育馆|运动场|文化活动中心", "icon": "⚽", "color": "#fd7e14"},
    "7-商业服务": {"keywords": "超市|便利店|商场|菜市场|餐饮|书店", "icon": "🛒", "color": "#ffc107"},
    "8-金融邮电": {"keywords": "银行|邮局|储蓄所|电信营业厅", "icon": "🏦", "color": "#6f42c1"},
    "9-社区服务": {"keywords": "社区服务中心|居委会|敬老院|养老院", "icon": "🏘️", "color": "#20c997"},
    "10-市政公用": {"keywords": "停车场|公共厕所|公交站|消防站", "icon": "🏗️", "color": "#17a2b8"},
    "11-行政管理": {"keywords": "街道办事处|派出所|政务服务中心", "icon": "🏛️", "color": "#6c757d"},
}

# 缓存
distance_cache = {}

def geocode_address(address):
    """将地址转换为精确坐标"""
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": AMAP_KEY,
        "address": address,
        "output": "JSON"
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if data['status'] == '1' and data.get('geocodes'):
            loc = data['geocodes'][0]['location']
            lon, lat = loc.split(',')
            return float(lat), float(lon)
    except Exception as e:
        print(f"地理编码失败: {e}")
    return None, None

def calculate_straight_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return round(R * c, 2)

def get_driving_distance(origin_lat, origin_lon, dest_lat, dest_lon):
    cache_key = f"driving_{origin_lat}_{origin_lon}_{dest_lat}_{dest_lon}"
    if cache_key in distance_cache:
        return distance_cache[cache_key]
    
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "key": AMAP_KEY,
        "origin": f"{origin_lon},{origin_lat}",
        "destination": f"{dest_lon},{dest_lat}",
        "output": "JSON"
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if data['status'] == '1' and data.get('route', {}).get('paths'):
            distance = round(float(data['route']['paths'][0]['distance']) / 1000, 2)
            distance_cache[cache_key] = distance
            return distance
    except Exception as e:
        print(f"驾车距离失败: {e}")
    return None

def get_transit_distance(origin_lat, origin_lon, dest_lat, dest_lon, city):
    cache_key = f"transit_{origin_lat}_{origin_lon}_{dest_lat}_{dest_lon}_{city}"
    if cache_key in distance_cache:
        return distance_cache[cache_key]
    
    url = "https://restapi.amap.com/v3/direction/transit/integrated"
    params = {
        "key": AMAP_KEY,
        "origin": f"{origin_lon},{origin_lat}",
        "destination": f"{dest_lon},{dest_lat}",
        "city": city,
        "cityd": city,
        "output": "JSON"
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if data['status'] == '1' and data.get('route', {}).get('transits'):
            distance = round(float(data['route']['transits'][0]['distance']) / 1000, 2)
            distance_cache[cache_key] = distance
            return distance
    except Exception as e:
        print(f"公交距离失败: {e}")
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/communities')
def get_communities():
    return jsonify({'communities': [{'name': c['name'], 'city': c['city'], 'address': c['address']} for c in PRESET_COMMUNITIES]})

@app.route('/api/geocode', methods=['POST'])
def geocode():
    data = request.json
    address = data.get('address', '')
    if not address:
        return jsonify({'error': '请输入地址'})
    
    lat, lon = geocode_address(address)
    if lat and lon:
        return jsonify({'success': True, 'lat': lat, 'lon': lon, 'address': address})
    else:
        return jsonify({'error': '未找到该地址'})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        community_name = data.get('community_name', '')
        custom_lat = data.get('custom_lat')
        custom_lon = data.get('custom_lon')
        custom_address = data.get('custom_address', '')
        search_radius = float(data.get('search_radius', 5))
        include_transit = data.get('include_transit', False)
        
        # 确定起点坐标
        if custom_lat and custom_lon:
            origin_lat = custom_lat
            origin_lon = custom_lon
            origin_name = custom_address or f"自定义坐标({origin_lat},{origin_lon})"
            city = "佛山"
        else:
            community = next((c for c in PRESET_COMMUNITIES if community_name in c['name']), None)
            if not community:
                return jsonify({'error': '社区不存在'}), 404
            origin_lat = community['lat']
            origin_lon = community['lon']
            origin_name = community['name']
            city = community['city']
        
        # 搜索周边设施
        results_by_category = {}
        all_facilities = []
        
        for cat_id, cat_info in FACILITY_CATEGORIES.items():
            cat_name = cat_id.split('-')[1] if '-' in cat_id else cat_id
            results_by_category[cat_id] = {
                "name": cat_name,
                "icon": cat_info["icon"],
                "color": cat_info["color"],
                "count": 0,
                "items": []
            }
            
            search_url = "https://restapi.amap.com/v3/place/around"
            search_resp = requests.get(search_url, params={
                "key": AMAP_KEY,
                "location": f"{origin_lon},{origin_lat}",
                "radius": search_radius * 1000,
                "keywords": cat_info["keywords"],
                "city": city,
                "offset": 20,
                "output": "JSON"
            })
            search_data = search_resp.json()
            
            if search_data.get('pois'):
                for poi in search_data['pois']:
                    poi_name = poi.get('name', '')
                    poi_addr = poi.get('address', '')
                    loc = poi.get('location', '')
                    
                    if not loc:
                        continue
                    
                    lon, lat = loc.split(',')
                    dest_lat = float(lat)
                    dest_lon = float(lon)
                    
                    straight_dist = calculate_straight_distance(origin_lat, origin_lon, dest_lat, dest_lon)
                    driving_dist = get_driving_distance(origin_lat, origin_lon, dest_lat, dest_lon)
                    
                    if not driving_dist or driving_dist > search_radius:
                        continue
                    
                    transit_dist = None
                    if include_transit:
                        transit_dist = get_transit_distance(origin_lat, origin_lon, dest_lat, dest_lon, city)
                    
                    facility_item = {
                        'name': poi_name,
                        'address': poi_addr,
                        'straight_distance': straight_dist,
                        'driving_distance': driving_dist,
                        'transit_distance': transit_dist
                    }
                    
                    results_by_category[cat_id]["count"] += 1
                    results_by_category[cat_id]["items"].append(facility_item)
                    all_facilities.append({
                        'name': poi_name,
                        'category': cat_name,
                        'address': poi_addr,
                        'straight_distance': straight_dist,
                        'driving_distance': driving_dist,
                        'transit_distance': transit_dist
                    })
                    
                    time.sleep(0.02)
        
        # 排序
        for cat_id in results_by_category:
            results_by_category[cat_id]["items"].sort(key=lambda x: x['driving_distance'])
        all_facilities.sort(key=lambda x: x['driving_distance'])
        
        total = len(all_facilities)
        
        # 计算总体可及性
        if total > 0:
            avg_driving = sum(f['driving_distance'] for f in all_facilities) / total
            total_accessibility = (total / avg_driving) * 10
        else:
            avg_driving = 0
            total_accessibility = 0
        
        # 计算每个类别的可及性指数
        category_accessibility = {}
        for cat_id, cat_data in results_by_category.items():
            cat_items = cat_data["items"]
            cat_count = len(cat_items)
            if cat_count > 0:
                cat_avg_distance = sum(item['driving_distance'] for item in cat_items) / cat_count
                cat_accessibility = (cat_count / cat_avg_distance) * 10
            else:
                cat_avg_distance = 0
                cat_accessibility = 0
            
            category_accessibility[cat_id] = {
                "name": cat_data["name"],
                "icon": cat_data["icon"],
                "count": cat_count,
                "avg_distance": round(cat_avg_distance, 2),
                "accessibility": round(cat_accessibility, 3)
            }
        
        return jsonify({
            'success': True,
            'result': {
                'origin': {
                    'name': origin_name,
                    'lat': origin_lat,
                    'lon': origin_lon,
                    'address': custom_address or (community.get('address') if not custom_lat else '')
                },
                'search_radius': search_radius,
                'total_facilities': total,
                'facilities_by_category': results_by_category,
                'all_facilities': all_facilities,
                'statistics': {
                    'avg_driving_distance': round(avg_driving, 2),
                    'accessibility': round(total_accessibility, 3),
                    'category_accessibility': category_accessibility
                }
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print('=' * 60)
    print('🏘️ 社区公共服务设施可及性分析系统')
    print('📊 11大类分类（含各类别独立可及性指数）')
    print('🌐 访问地址: http://127.0.0.1:5000')
    print('=' * 60)
    app.run(debug=True, port=5000, threaded=True)