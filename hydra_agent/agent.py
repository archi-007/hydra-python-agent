import logging
from hydra_agent.redis_proxy import RedisProxy
from hydra_agent.graphutils_operations import GraphOperations
from hydra_agent.hydra_graph import InitialGraph
from hydra_python_core import doc_maker
from requests import Session

logger = logging.getLogger(__file__)


class HydraAgent(Session):
    def __init__(self, entrypoint_url):
        self.entrypoint_url = entrypoint_url.strip().rstrip('/')
        self.redis_proxy = RedisProxy()
        self.redis_connection = self.redis_proxy.get_connection()
        self.graph_operations = GraphOperations(entrypoint_url,
                                                self.redis_proxy)
        super().__init__()
        jsonld_api_doc = super().get(self.entrypoint_url + '/vocab').json()
        self.api_doc = doc_maker.create_doc(jsonld_api_doc)
        self.initialize_graph()

    def initialize_graph(self):
        self.graph = InitialGraph()
        self.redis_connection.delete("apigraph")
        self.graph.main(self.entrypoint_url, self.api_doc, True)
        self.redis_connection.sadd("fs:url", self.entrypoint_url)

    def get(self, url):
        response = self.graph_operations.get_resource(url)
        if response is not None:
            return response

        response = super().get(url)

        if response.status_code == 200:
            self.graph_operations.get_processing(url, response.json())

        return response

    def put(self, url, new_object):
        response = super().put(url, json=new_object)

        if response.status_code == 201:
            url = response.headers['Location']
            self.graph_operations.put_processing(url, new_object)

        return response

    def post(self, url, updated_object):
        response = super().post(url, json=updated_object)

        if response.status_code == 200:
            self.graph_operations.post_processing(url, updated_object)

        return response

    def delete(self, url):
        response = super().delete(url)

        if response.status_code == 200:
            self.graph_operations.delete_processing(url)

        return response

if __name__ == "__main__":
    Agent = HydraAgent("http://localhost:8080/serverapi")

    new_object = {"@type": "Drone", "DroneState": "Simplified state",
                  "name": "Smart Drone", "model": "Hydra Drone",
                  "MaxSpeed": "999", "Sensor": "Wind"}

    response = Agent.put("http://localhost:8080/serverapi/DroneCollection/",
                         new_object)

    new_resource_url = response.headers['Location']

    logger.info(Agent.get(new_resource_url))

    new_object["name"] = "Updated Name"
    del new_object["@id"]
    print("esse aq")
    logger.info(Agent.post(new_resource_url, new_object))

    logger.info(Agent.delete(new_resource_url))

    logger.info(Agent.get("http://localhost:8080/serverapi/DroneCollection/"))

    #logger.info(Agent.get("http://localhost:8080/serverapi/DroneCollection/607cdfee-a1d4-4476-8bb5-93cc5955a408"))


    # logger.info(Agent.delete("http://localhost:8080/serverapi/DroneCollection/fd1e4cc5-6223-4e8a-b544-6dc9b2e60cf7"))
