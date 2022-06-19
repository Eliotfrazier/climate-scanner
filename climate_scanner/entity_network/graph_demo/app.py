#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Necessary API imports
from flask import Flask, request
from functools import wraps
from flask_restplus import Api, Resource, fields


# Graph modules
from neo4j_model import GraphConstructor
from entity_extraction import EntityExtractor


# Initialise application
app = Flask(__name__)

# Defining an authorisation Dict
authorizations = {
	'apikey': {
		'type': 'apiKey',
		'in': 'header',
		'name': 'Authorization'
	},
}

api = Api(app=app, authorizations=authorizations)

# Load in key from environment vars typically
# SWAGGER_KEY = os.environ.get('SWAGGER_KEY')
SWAGGER_KEY = '1234'


# Initialize Graph Handler and Entity Extractor Objects
graph = GraphConstructor()
extractor = EntityExtractor()


##############################################################################
#
#	A function wrapper for the end-point methods to provide some rudimentary
#	security.
#
#	TODO: host key for security, rather than keeping in codebase
#
##############################################################################

def key_required(func):
	@wraps(func)
	def decorated(*args, **kwargs):
		end_key = None

		if 'Authorization' in request.headers:
			end_key = request.headers['Authorization']

		if not end_key:
			return {'status': 401, 'message': 'Api Key required'}

		if end_key != SWAGGER_KEY:
			return {'status': 401, 'message': 'Api Key Incorrect'}

		print('API Key: {}'.format(end_key))
		return func(*args, **kwargs)

	return decorated


# Define a namespace. These are used to divide up different modules of the api
# The api.namespace() function creates a new namespace with a URL prefix.
# The description field will be used in the Swagger UI to describe this set of methods.
name_space = api.namespace('TrendScanner Graph API',
							description='An api for testing the TrendScanner Graph Model.')

##########################################################################################
#
#	Define class for the route and inherit from restplus Resource.
# 	RESTful resources are used to organize different the API endpoints
# 	This example shows only one endpoint but if you add more they are all displayed/
# 	documented on the same UI page
#
#
##########################################################################################

graph_data = api.model('Graph Model', {
	'entities': fields.List(required=True,
					  description="List of incoming entities",
					  example=[
						  ['Chris Ballinger', 'PERSON',
							 {'entityType': None, 'wiki_classes': None,
							 'url': None, 'dbPediaIri': None}],
						  ['the Future Blockchain Summit', 'ORG',
							 {'entityType': None, 'wiki_classes': None,
							 'url': None, 'dbPediaIri': None}],
						  ['Ford', 'ORG', {'entityType': ['Agent', 'Organisation', 'Company'], 'wiki_classes': ['automobile manufacturer', 'sponsor', 'car brand', 'manufacturing company', 'legal person'], 'url': 'http://en.wikipedia.org/wiki/Ford_Motor_Company', 'dbPediaIri': 'http://dbpedia.org/resource/Ford_Motor_Company'}]],
					  cls_or_instance=fields.Arbitrary())
})

node_data = api.model('Node Model', {

	'name': fields.String(
		required=False, description="Name of the entity", example='Dubai'),

	'entity': fields.String(
		required=False, description="Entity identifier", example='GPE'),

	'entity_type': fields.List(required=False, description="List of entity types",
						  example=["City", "Settlement","Place"], cls_or_instance=fields.String),

	'wiki_classes': fields.List(required=False, description="List of wiki classes",
						 example=["city", "community","big city"], cls_or_instance=fields.String),


	'url': fields.String(
		required=False, description="URL of entity general info", example='http://en.wikipedia.org/wiki/Dubai'),

	'dbpedia_uri': fields.String(
		required=False, description="URL of entity info in dbpedia", example='http://dbpedia.org/resource/Dubai'),
})


text_data = api.model('Text Model', {
	'text': fields.String(
		required=True, description="Text for processing", example='Sir Keir Starmer has urged the government to invest urgently in jobs that benefit the environment. ' \
						 'The Labour leader wants £30bn spent to support up to 400,000 “green” jobs in manufacturing' \
						 ' and low-carbon industries.' \
						 'The government says it will create thousands of green jobs as part of its overall climate strategy.' \
						 'But official statistics show no measurable increase in environment-based jobs in recent years.' \
						 'Speaking to the BBC as he begins a two-day visit to Scotland, Sir Keir blamed this on a' \
						 ' "chasm between soundbites and action”.' \
						 'He and PM Boris Johnson are both in Scotland this week, showcasing their green credentials' \
						 ' ahead of Novembers COP 26 climate summit in Glasgow.' \
						 'Criticising the governments green jobs record, Sir Keir points to its decision to' \
						 ' scrap support for solar power and onshore wind energy, and a scheme to help' \
						 ' householders in England insulate their homes.' \
						 'He said: “It’s the government’s failure to match its rhetoric with reality that’s ' \
						 'led to this, They have used soundbites with no substance.' \
						 '“They have quietly been unpicking and dropping critical' \
						 ' commitments when it comes to the climate crisis and the future economy.' \
						 '“It’s particularly concerning when it comes to COP 26.' \
						 '"Leading by example is needed, but just when we need leadership' \
						 ' from the prime minister on the global stage, here in the UK we have a prime' \
						 ' minister who, frankly, is missing in action."')
})


@name_space.route('/nodes/')
class ManageNodes(Resource):

	@name_space.doc(security='apikey')
	@api.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Internal Server Error'},
			  params={'entityType': 'Specify the entity type to filter the resulting nodes. Common entity types are PERSON, ORG, GPE. Leave empty for retrieving all the nodes'})
	@key_required
	def get(self):
		"""Get nodes by entity type
		<strong>Implementation Notes</strong>.
		<p>
		Get a list of nodes with all the associated properties. It is possible to filter
		by entity type.
		</p>
		"""
		try:

			entity_type = request.args.get('entityType')
			results = graph.get_nodes(entity_type)

			return {'status': 200, 'nodes': results}

		except KeyError as e:
			name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except Exception as e:
			name_space.abort(500,  status="Error within app: " + str(e), statusCode="500")


	# Defining a get rest functionality to get disambiguated location object
	@name_space.doc(security='apikey')
	@api.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Internal Server Error'})
	@api.expect(graph_data, validate=False)
	@key_required
	def post(self):
		"""Create nodes and connections
		<strong>Implementation Notes</strong>.
		<p>
		Insert entities as nodes to the graph and generates connections between each pair of nodes,
		generating a fully connected graph.
		</p>
		"""
		try:
			data = api.payload
			success = graph.create_nodes(data['entities'])

			if(success):
				return {'status': 200, 'message': 'Nodes and relationships created successfully'}
			else:
				name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except KeyError as e:
			name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except Exception as e:
			name_space.abort(500,  status="Error within app: " + str(e), statusCode="500")


	@name_space.doc(security='apikey')
	@api.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Internal Server Error'},
			  params={'uid': 'Unique node identifier'})
	@api.expect(node_data, validate=False)
	@key_required
	def put(self):
		"""Update node properties
		<strong>Implementation Notes</strong>.
		<p>
		Provide the node uid as param and specify the fields to modify with the new data
		 in the body of the request.
		</p>
		"""
		try:
			uid = request.args.get('uid')
			data = api.payload
			success = graph.update_node(uid,data)
			#success = True

			if(success):
				return {'status': 200, 'message': 'Node updated successfully'}
			else:
				name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except KeyError as e:
			name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except Exception as e:
			name_space.abort(500,  status="Error within app: " + str(e), statusCode="500")


	@name_space.doc(security='apikey')
	@api.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Internal Server Error'},
			  params={'uid': 'Unique node identifier'})
	@key_required
	def delete(self):
		"""Delete node
		<strong>Implementation Notes</strong>.
		<p>
		Provide the node uid as param and the node will be deleted.
		All the relationships with other nodes are deleted as well.
		</p>
		"""
		try:
			uid = request.args.get('uid')
			success = graph.delete_node(uid)

			if(success):
				return {'status': 200, 'message': 'Node deleted successfully'}
			else:
				name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except KeyError as e:
			name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except Exception as e:
			name_space.abort(500,  status="Error within app: " + str(e), statusCode="500")



@name_space.route('/extraction/')
class EntityExtraction(Resource):

	# Defining a get rest functionality to get disambiguated location object
	@name_space.doc(security='apikey')
	@api.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Internal Server Error'})
	@api.expect(text_data, validate=False)
	@key_required
	def post(self):
		"""Extract entities from text
		<strong>Implementation Notes</strong>.
		<p>
		Send a text fragment in the body. The entities will be extracted and returned as response.
		</p>
		"""
		try:
			data = api.payload
			print(data['text'])
			entities = extractor.get_annotations(data['text'])

			return {'status': 200, 'message': entities}

		except KeyError as e:
			name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except Exception as e:
			name_space.abort(500,  status="Error within app: " + str(e), statusCode="500")


@name_space.route('/entity-network/')
class EntityGraphBuild(Resource):

	# Defining a get rest functionality to get disambiguated location object
	@name_space.doc(security='apikey')
	@api.doc(responses={200: 'OK', 400: 'Invalid Argument', 500: 'Internal Server Error'})
	@api.expect(text_data, validate=False)
	@key_required
	def post(self):
		"""Create graph from text
		<strong>Implementation Notes</strong>.
		<p>
		Send a text fragment in the body. The entities will be extracted and the graph
		will be formed from those entities. The list of entities is obtained as response.
		</p>
		"""
		try:
			data = api.payload
			entities = extractor.get_annotations(data['text'])
			success = graph.create_nodes(entities)

			if(success):
				return {'status': 200, 'message': entities}
			else:
				name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except KeyError as e:
			name_space.abort(400,  status="Could not retrieve necessary payload information", statusCode="400")

		except Exception as e:
			name_space.abort(500,  status="Error within app: " + str(e), statusCode="500")





#if __name__ == '__main__':
#	app.run(debug=True)

