from flask import Blueprint, request, jsonify
from models import db, Location, Container, Collection
from datetime import datetime, timedelta
from sqlalchemy import func

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/summary', methods=['GET'])
def get_summary():
    """Получение сводной информации"""
    try:
        # Параметры фильтрации
        period = request.args.get('period', 'week')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Определение диапазона дат
        end_date = datetime.utcnow()
        
        if period == 'day':
            start_date = end_date - timedelta(days=1)
        elif period == 'week':
            start_date = end_date - timedelta(weeks=1)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'custom' and start_date_str and end_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        else:
            start_date = end_date - timedelta(weeks=1)
        
        # Подсчет статистики
        total_collections = Collection.query.filter(
            Collection.collected_at >= start_date,
            Collection.collected_at <= end_date
        ).count()
        
        # Статистика по контейнерам
        total_containers = Container.query.count()
        full_containers = Container.query.filter_by(status='full').count()
        empty_containers = Container.query.filter_by(status='empty').count()
        partial_containers = Container.query.filter_by(status='partial').count()
        
        # Средний уровень заполнения
        avg_fill_rate = db.session.query(
            func.avg(Container.fill_level)
        ).scalar() or 0
        
        summary = {
            'totalCollections': total_collections,
            'averageFillRate': round(float(avg_fill_rate), 1),
            'fullContainers': full_containers,
            'emptyContainers': empty_containers,
            'partialContainers': partial_containers,
            'totalContainers': total_containers,
            'period': period,
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat()
        }
        
        return jsonify(summary), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения сводки: {str(e)}'}), 500


@reports_bp.route('/collections', methods=['GET'])
def get_collections():
    """Получение списка сборов мусора"""
    try:
        # Параметры фильтрации
        location_id = request.args.get('location_id')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = Collection.query
        
        if location_id:
            query = query.filter_by(location_id=location_id)
        
        # Сортировка по дате (сначала новые)
        query = query.order_by(Collection.collected_at.desc())
        
        # Пагинация
        collections = query.limit(limit).offset(offset).all()
        total = query.count()
        
        return jsonify({
            'collections': [c.to_dict() for c in collections],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения истории сборов: {str(e)}'}), 500


@reports_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Получение детальной статистики"""
    try:
        # Статистика по площадкам
        locations_count = Location.query.count()
        locations_full = Location.query.filter_by(status='full').count()
        locations_empty = Location.query.filter_by(status='empty').count()
        locations_partial = Location.query.filter_by(status='partial').count()
        
        # Статистика по контейнерам
        containers_count = Container.query.count()
        containers_full = Container.query.filter_by(status='full').count()
        containers_empty = Container.query.filter_by(status='empty').count()
        containers_partial = Container.query.filter_by(status='partial').count()
        
        # Площадки, требующие внимания (полные или давно не обслуживались)
        threshold_date = datetime.utcnow() - timedelta(days=3)
        locations_need_attention = Location.query.filter(
            (Location.status == 'full') | 
            (Location.last_collection < threshold_date) |
            (Location.last_collection == None)
        ).all()
        
        statistics = {
            'locations': {
                'total': locations_count,
                'full': locations_full,
                'empty': locations_empty,
                'partial': locations_partial,
                'needAttention': len(locations_need_attention),
                'attentionList': [loc.to_dict() for loc in locations_need_attention[:10]]
            },
            'containers': {
                'total': containers_count,
                'full': containers_full,
                'empty': containers_empty,
                'partial': containers_partial
            }
        }
        
        return jsonify(statistics), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения статистики: {str(e)}'}), 500


@reports_bp.route('/charts/fill-levels', methods=['GET'])
def get_fill_levels_chart():
    """Получение данных для графика уровней заполнения"""
    try:
        locations = Location.query.all()
        
        data = []
        for location in locations:
            avg_fill = sum(c.fill_level for c in location.containers) / len(location.containers) if location.containers else 0
            data.append({
                'name': location.name,
                'fillLevel': round(avg_fill, 1),
                'containers': len(location.containers)
            })
        
        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения данных графика: {str(e)}'}), 500

