import types
from heka.encoders import ProtobufEncoder
from heka.tests.helpers import decode_message
from heka.message import Message, Field, first_value

class TestWireFormat(object):
    def build_msg(self, value):
        msg = Message(uuid='0123456789012345', 
                type='demo',
                timestamp=1000000)
        f = msg.fields.add()
        f.name = 'myfield'
        f.representation = ""

        if isinstance(value, types.BooleanType):
            f.value_type = Field.BOOL
            f.value_bool.append(bool(value))
        elif isinstance(value, types.IntType):
            f.value_type = Field.INTEGER
            f.value_integer.append(value)
        elif isinstance(value, types.FloatType):
            f.value_type = Field.DOUBLE
            f.value_double.append(value)
        elif isinstance(value, basestring):
            f.value_type = Field.STRING
            f.value_string.append(value)
        return f.value_type, msg

    def render(self, msg, ftype):
        bytes = msg.SerializeToString()

        if ftype == Field.DOUBLE:
            name = 'Float'
        elif ftype == Field.INTEGER:
            name = 'Int'
        elif ftype == Field.STRING:
            name = 'Str'
        elif ftype == Field.BOOL:
            name = 'Bool'

        print "\n\n\n"
        print "# %s Bytes: %d" % (name, len(bytes))
        print "%s Bytes:", (name, ":".join("%02x" % (ord(c)) for c in bytes))
        print "\n\n"
        return bytes

    def check_bytes(self, bytes, value):
        new_msg = Message()
        new_msg.ParseFromString(bytes)

        assert new_msg.uuid == '0123456789012345'
        assert new_msg.type == 'demo'
        assert new_msg.timestamp == 1000000
        assert first_value(new_msg, 'myfield') == value

    def runtest(self, value):
        enc = ProtobufEncoder()
        ftype, msg = self.build_msg(value)
        bytes = self.render(msg, ftype)
        self.check_bytes(bytes, value)

    def test_float_field(self):
        value = 3.14
        self.runtest(value)

    def test_str_field(self):
        value = 'hello'
        self.runtest(value)

    def test_bool_field(self):
        value = True
        self.runtest(value)
        
    def test_int_field(self):
        value = 5
        self.runtest(value)

    def test_bytes_field(self):
        value = 'some_bytes'
        enc = ProtobufEncoder()

        msg = Message(uuid='0123456789012345', 
                type='demo',
                timestamp=1000000)
        f = msg.fields.add()
        f.name = 'myfield'
        f.representation = ""

        f.value_type = Field.BYTES
        f.value_bytes.append(value)

        bytes = msg.SerializeToString()

        name = 'Bytes'
        print "\n\n\n"
        print "# %s Bytes: %d" % (name, len(bytes))
        print "%s Bytes:", (name, ":".join("%02x" % (ord(c)) for c in bytes))
        print "\n\n"

        self.check_bytes(bytes, value)

