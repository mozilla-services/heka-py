# Compil ethe protocol buffer code
#

all:
	protoc -I=protobuf --python_out=heka protobuf/message.proto

.PHONY: docs
docs:
	cd docs
	make -f ./Makefile html
