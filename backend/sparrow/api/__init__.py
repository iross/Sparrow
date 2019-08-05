from flask import Flask, Blueprint
from flask_restful import Resource, reqparse, inputs, abort
from sqlalchemy.schema import Table
from sqlalchemy import MetaData
from flask import jsonify
from flask_jwt_extended import jwt_required, jwt_optional, get_jwt_identity
from textwrap import dedent
from datetime import datetime

from .base import API

# eventually should use **Marshmallow** or similar
# for parsing incoming API requests

def date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d").date()

def infer_primary_key(table):
    pk = table.primary_key
    if len(pk) == 1:
        return list(pk)[0]
    # Check PK column a few possible ways
    for i in ('id', table.name+'_id'):
        pk = table.c.get(i, None)
        if pk is not None: return pk
    return list(table.c)[0]

def infer_type(t):
    # Really hackish
    try:
        type = t.type.python_type
        if type == bool:
            type = inputs.boolean
        return type
    except NotImplementedError:
        return None

def build_description(argument):
    """
    Build a description for a parser argument
    """
    type = argument.type
    usage = None
    typename = type.__name__
    if typename == 'Decimal':
        typename = 'numeric'
    elif type == list:
        typename = 'array'
        usage = "Match any of the array items"
    elif type == str:
        usage = dedent("""
        Use [*PostgreSQL* **LIKE** wildcards](https://www.postgresql.org/docs/current/functions-matching.html)
        (e.g. %,_,*) for fuzzy matching
        """).strip()

    return dict(
        name=argument.name,
        default=argument.default,
        type=typename,
        description=argument.help,
        usage=usage
    )

errors = dict(
    TypeError=dict(message="Could not serialize JSON data"))

class APIv1(API):
    """
    Version 1 API for Lab Data Interface

    Includes functionality for autogenerating routes
    from database tables and views.

    Each autogenerated endpoint has a `/describe` URL that
    provides API usage data.
    """
    def __init__(self, database):
        self.db = database
        self.blueprint = Blueprint('api', __name__)
        super().__init__(self.blueprint, errors=errors)
        self.route_descriptions = []
        self.create_description_model()

    def create_description_model(self):
        route_descriptions = self.route_descriptions
        class APIDescriptionModel(Resource):
            def get(self):
                return dict(
                    route='/api/v1',
                    description='Version 1 API for Sparrow',
                    routes=route_descriptions)

        self.add_resource(APIDescriptionModel, '/', '/describe')


    def build_route(self, tablename, **kwargs):
        schema = kwargs.pop('schema', None)
        db = self.db
        table = db.reflect_table(tablename, schema=schema)

        schema_qualified_tablename = tablename
        if schema is not None:
            schema_qualified_tablename = schema+"."+schema_qualified_tablename
        description = f"Autogenerated route for table `{schema_qualified_tablename}`"

        primary_key = kwargs.pop("primary_key", None)
        if primary_key is not None:
            key = table.c[primary_key]
        else:
            key = infer_primary_key(table)

        parser = reqparse.RequestParser()
        parser.add_argument('offset', type=int, help='Query offset', default=None)
        parser.add_argument('limit', type=int, help='Query limit', default=None)
        parser.add_argument('all', type=bool, help='Return all rows', default=False)

        # Manage row-level permissions
        is_access_controlled = False
        for name, column in table.c.items():
            # We handle embargo at the application rather than database level
            if name == 'is_public':
                parser.add_argument('private', type=bool,
                    help='Return private data', default=False)
                continue

            try:
                type = infer_type(column)
                if type == dict:
                    # We don't yet support dict types
                    continue
                if type == datetime:
                    start = str(name)+"_start"
                    end = str(name)+"_end"
                    parser.add_argument(start, type=date,
                        help=f"Beginning date (e.g. 2017-01-02)")
                    parser.add_argument(end, type=date,
                        help=f"End date (e.g. 2017-01-02)")
                    continue
                typename = type.__name__
                parser.add_argument(str(name), type=type,
                    help=None)
            except:
                continue

        # Set up information about
        # table descriptions

        route = f"/{tablename}"
        tname = infer_type(key).__name__
        if tname != 'int':
            tname = 'string'
        get_route = f"/<{tname}:{key.name}>"

        basicInfo = dict(
            route=route,
            table=table.name,
            schema=table.schema,
            description=description,
            usage_info="Pass the parameter `?all=1` to return all rows instead of API description"
        )
        self.route_descriptions.append(basicInfo)

        class TableModel(Resource):
            def describe(self):
                """
                If no parameters are passed, return the API route's
                description object. This conforms to the convention
                of the Macrostrat API.
                """
                args = [build_description(a) for a in parser.args]

                return dict(
                    **basicInfo,
                    arguments=args,
                    record=dict(
                        route=get_route,
                        key=key.name,
                        type=tname))

            @jwt_optional
            def get(self):

                args = parser.parse_args()

                # Check identity and abort if unauthorized
                identity = get_jwt_identity()
                # If we are logged in, always request private
                # (this should probably be handled better in the long term)
                #private = identity is not None
                private = args.pop('private', False)
                if identity:
                    private = True
                if private and not identity:
                    # Should throw a better error
                    return abort(401)

                should_describe = True

                # Get offset and limit at outset
                offset = args.pop('offset', None)
                limit = args.pop('limit', None)
                if offset is not None and limit is not None:
                    should_describe = False

                filters = []

                for k,col in table.c.items():
                    if k == 'is_public':
                        # To return embargoed data, we must
                        # have a valid JSON Web Token
                        if not private:
                            filters.append(col == True)
                        continue

                    # Should have a better way to do this
                    if infer_type(col) == datetime:
                        date_start = args.pop(str(k)+"_start", None)
                        date_end = args.pop(str(k)+"_end", None)
                        if date_start is not None:
                            filters.append(col >= date_start)
                            should_describe = False
                        if date_end is not None:
                            filters.append(col <= date_end)
                            should_describe = False
                        continue

                    val = args.pop(k, None)
                    if val is None: continue

                    should_describe = False
                    if infer_type(col) == str:
                        filters.append(col.like(val))
                    else:
                        filters.append(col==val)

                if args.pop('all', False):
                    should_describe = False

                # Bail to describing query optionally
                if should_describe:
                    return self.describe()

                # Begin querying after filters are assembled

                try:
                    q = db.session.query(table)
                    for filter in filters:
                        q = q.filter(filter)

                    count = q.count()

                    if offset is not None:
                        q = q.offset(offset)
                    if limit is not None:
                        q = q.limit(limit)
                    # Save the count of the query
                    response = q.all()

                    status = 200
                    headers = {'x-total-count': count}
                    return response, status, headers

                except:
                    db.session.rollback()
                    # Better error handling is a must here
                    return jsonify(error='Query Error'), 410


        class RecordModel(Resource):
            @jwt_required
            def get(self, id):
                # Should fail if more than one record is returned
                return (db.session.query(table)
                    .filter(key==id)
                    .first())

        # Dynamically change class name,
        # this kind of metaprogrammy wizardry
        # may cause problems later
        TableModel.__name__ = tablename
        RecordModel.__name__ = tablename+'_record'

        self.add_resource(TableModel, route, route+"/")
        self.add_resource(RecordModel, get_route)
