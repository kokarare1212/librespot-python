# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: spotify/login5/v3/challenges/hashcash.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import duration_pb2 as google_dot_protobuf_dot_duration__pb2
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor.FileDescriptor(
    name="spotify/login5/v3/challenges/hashcash.proto",
    package="spotify.login5.v3.challenges",
    syntax="proto3",
    serialized_options=b"\n\024com.spotify.login5v3",
    create_key=_descriptor._internal_create_key,
    serialized_pb=b'\n+spotify/login5/v3/challenges/hashcash.proto\x12\x1cspotify.login5.v3.challenges\x1a\x1egoogle/protobuf/duration.proto"3\n\x11HashcashChallenge\x12\x0e\n\x06prefix\x18\x01 \x01(\x0c\x12\x0e\n\x06length\x18\x02 \x01(\x05"O\n\x10HashcashSolution\x12\x0e\n\x06suffix\x18\x01 \x01(\x0c\x12+\n\x08\x64uration\x18\x02 \x01(\x0b\x32\x19.google.protobuf.DurationB\x16\n\x14\x63om.spotify.login5v3b\x06proto3',
    dependencies=[
        google_dot_protobuf_dot_duration__pb2.DESCRIPTOR,
    ],
)

_HASHCASHCHALLENGE = _descriptor.Descriptor(
    name="HashcashChallenge",
    full_name="spotify.login5.v3.challenges.HashcashChallenge",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
        _descriptor.FieldDescriptor(
            name="prefix",
            full_name="spotify.login5.v3.challenges.HashcashChallenge.prefix",
            index=0,
            number=1,
            type=12,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"",
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
        _descriptor.FieldDescriptor(
            name="length",
            full_name="spotify.login5.v3.challenges.HashcashChallenge.length",
            index=1,
            number=2,
            type=5,
            cpp_type=1,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=109,
    serialized_end=160,
)

_HASHCASHSOLUTION = _descriptor.Descriptor(
    name="HashcashSolution",
    full_name="spotify.login5.v3.challenges.HashcashSolution",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
        _descriptor.FieldDescriptor(
            name="suffix",
            full_name="spotify.login5.v3.challenges.HashcashSolution.suffix",
            index=0,
            number=1,
            type=12,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"",
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
        _descriptor.FieldDescriptor(
            name="duration",
            full_name="spotify.login5.v3.challenges.HashcashSolution.duration",
            index=1,
            number=2,
            type=11,
            cpp_type=10,
            label=1,
            has_default_value=False,
            default_value=None,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=162,
    serialized_end=241,
)

_HASHCASHSOLUTION.fields_by_name[
    "duration"
].message_type = google_dot_protobuf_dot_duration__pb2._DURATION
DESCRIPTOR.message_types_by_name["HashcashChallenge"] = _HASHCASHCHALLENGE
DESCRIPTOR.message_types_by_name["HashcashSolution"] = _HASHCASHSOLUTION
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

HashcashChallenge = _reflection.GeneratedProtocolMessageType(
    "HashcashChallenge",
    (_message.Message,),
    {
        "DESCRIPTOR": _HASHCASHCHALLENGE,
        "__module__": "spotify.login5.v3.challenges.hashcash_pb2"
        # @@protoc_insertion_point(class_scope:spotify.login5.v3.challenges.HashcashChallenge)
    },
)
_sym_db.RegisterMessage(HashcashChallenge)

HashcashSolution = _reflection.GeneratedProtocolMessageType(
    "HashcashSolution",
    (_message.Message,),
    {
        "DESCRIPTOR": _HASHCASHSOLUTION,
        "__module__": "spotify.login5.v3.challenges.hashcash_pb2"
        # @@protoc_insertion_point(class_scope:spotify.login5.v3.challenges.HashcashSolution)
    },
)
_sym_db.RegisterMessage(HashcashSolution)

DESCRIPTOR._options = None
# @@protoc_insertion_point(module_scope)
