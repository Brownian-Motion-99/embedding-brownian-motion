.PHONY: vdb 

vdb:
	docker exec -it threads-vector-db psql -U postgres -d threads_vector

