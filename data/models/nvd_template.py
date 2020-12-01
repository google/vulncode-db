# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# The models below are generated with sqlacodegen which creates a SqlAlchemy
# description from a given SQL schema which is useful since we only have the
# DB schema for the NVD database.
#
# N.B. Make sure to replace "Base" with "AbstractConcreteBase" since we use
# inheritance in another file.
#
# Documentation: https://pypi.org/project/sqlacodegen/
# Executed: ./sqlacodegen mysql://[name]:[pass]@localhost/cve
# coding: utf-8
from sqlalchemy import Column, Float, String, TIMESTAMP, Text, DateTime
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.ext.declarative import AbstractConcreteBase


class Affect(AbstractConcreteBase):
    __tablename__ = "affects"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    nvd_json_id = Column(INTEGER(10), index=True)
    vendor = Column(String(255))
    product = Column(String(255))
    version = Column(String(255))


class Cert(AbstractConcreteBase):
    __tablename__ = "certs"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    deleted_at = Column(DateTime, index=True)
    jvn_id = Column(INTEGER(10), index=True)
    nvd_json_id = Column(INTEGER(10), index=True)
    title = Column(Text)
    link = Column(Text)


class Cpe(AbstractConcreteBase):
    __tablename__ = "cpes"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    jvn_id = Column(INTEGER(10), index=True)
    nvd_xml_id = Column(INTEGER(10), index=True)
    nvd_json_id = Column(INTEGER(10), index=True)
    uri = Column(String(255), index=True)
    formatted_string = Column(String(255), index=True)
    well_formed_name = Column(Text)
    part = Column(String(255), index=True)
    vendor = Column(String(255), index=True)
    product = Column(String(255), index=True)
    version = Column(String(255))
    update = Column(String(255))
    edition = Column(String(255))
    language = Column(String(255))
    software_edition = Column(String(255))
    target_sw = Column(String(255))
    target_hw = Column(String(255))
    other = Column(String(255))
    version_start_excluding = Column(String(255))
    version_start_including = Column(String(255))
    version_end_excluding = Column(String(255))
    version_end_including = Column(String(255))


class CveDetail(AbstractConcreteBase):
    __tablename__ = "cve_details"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    cve_id = Column(String(255), index=True)


class Cvss2(AbstractConcreteBase):
    __tablename__ = "cvss2"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    nvd_xml_id = Column(INTEGER(10), index=True)
    jvn_id = Column(INTEGER(10), index=True)
    vector_string = Column(String(255))
    access_vector = Column(String(255))
    access_complexity = Column(String(255))
    authentication = Column(String(255))
    confidentiality_impact = Column(String(255))
    integrity_impact = Column(String(255))
    availability_impact = Column(String(255))
    base_score = Column(Float(asdecimal=True))
    severity = Column(String(255))


class Cvss2Extra(AbstractConcreteBase):
    __tablename__ = "cvss2_extras"

    nvd_json_id = Column(INTEGER(10), index=True)
    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    nvd_xml_id = Column(INTEGER(10))
    jvn_id = Column(INTEGER(10))
    vector_string = Column(String(255))
    access_vector = Column(String(255))
    access_complexity = Column(String(255))
    authentication = Column(String(255))
    confidentiality_impact = Column(String(255))
    integrity_impact = Column(String(255))
    availability_impact = Column(String(255))
    base_score = Column(Float(asdecimal=True))
    severity = Column(String(255))
    exploitability_score = Column(Float(asdecimal=True))
    impact_score = Column(Float(asdecimal=True))
    obtain_all_privilege = Column(TINYINT(1))
    obtain_user_privilege = Column(TINYINT(1))
    obtain_other_privilege = Column(TINYINT(1))
    user_interaction_required = Column(TINYINT(1))


class Cvss3(AbstractConcreteBase):
    __tablename__ = "cvss3"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    nvd_json_id = Column(INTEGER(10), index=True)
    jvn_id = Column(INTEGER(10), index=True)
    vector_string = Column(String(255))
    attack_vector = Column(String(255))
    attack_complexity = Column(String(255))
    privileges_required = Column(String(255))
    user_interaction = Column(String(255))
    scope = Column(String(255))
    confidentiality_impact = Column(String(255))
    integrity_impact = Column(String(255))
    availability_impact = Column(String(255))
    base_score = Column(Float(asdecimal=True))
    base_severity = Column(String(255))
    exploitability_score = Column(Float(asdecimal=True))
    impact_score = Column(Float(asdecimal=True))


class Cwe(AbstractConcreteBase):
    __tablename__ = "cwes"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    nvd_xml_id = Column(INTEGER(10), index=True)
    nvd_json_id = Column(INTEGER(10), index=True)
    jvn_id = Column(INTEGER(10), index=True)
    cwe_id = Column(String(255))


class Description(AbstractConcreteBase):
    __tablename__ = "descriptions"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    nvd_json_id = Column(INTEGER(10), index=True)
    lang = Column(String(255))
    value = Column(Text)


class EnvCpe(AbstractConcreteBase):
    __tablename__ = "env_cpes"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    cpe_id = Column(INTEGER(10), index=True)
    uri = Column(String(255), index=True)
    formatted_string = Column(String(255), index=True)
    well_formed_name = Column(Text)
    part = Column(String(255))
    vendor = Column(String(255))
    product = Column(String(255))
    version = Column(String(255))
    update = Column(String(255))
    edition = Column(String(255))
    language = Column(String(255))
    software_edition = Column(String(255))
    target_sw = Column(String(255))
    target_hw = Column(String(255))
    other = Column(String(255))
    version_start_excluding = Column(String(255))
    version_start_including = Column(String(255))
    version_end_excluding = Column(String(255))
    version_end_including = Column(String(255))


class FeedMeta(AbstractConcreteBase):
    __tablename__ = "feed_meta"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    url = Column(String(255))
    hash = Column(String(255))
    last_modified_date = Column(String(255))


class Jvn(AbstractConcreteBase):
    __tablename__ = "jvns"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    cve_detail_id = Column(INTEGER(10), index=True)
    cve_id = Column(String(255), index=True)
    title = Column(String(255))
    summary = Column(Text)
    jvn_link = Column(String(255))
    jvn_id = Column(String(255))
    published_date = Column(TIMESTAMP)
    last_modified_date = Column(TIMESTAMP)


class NvdJson(AbstractConcreteBase):
    __tablename__ = "nvd_jsons"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    cve_detail_id = Column(INTEGER(10), index=True)
    cve_id = Column(String(255), index=True)
    published_date = Column(TIMESTAMP)
    last_modified_date = Column(TIMESTAMP)


class NvdXml(AbstractConcreteBase):
    __tablename__ = "nvd_xmls"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    cve_detail_id = Column(INTEGER(10), index=True)
    cve_id = Column(String(255), index=True)
    summary = Column(Text)
    published_date = Column(TIMESTAMP)
    last_modified_date = Column(TIMESTAMP)


class Reference(AbstractConcreteBase):
    __tablename__ = "references"

    id = Column(INTEGER(10), primary_key=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    deleted_at = Column(TIMESTAMP, index=True)
    nvd_xml_id = Column(INTEGER(10), index=True)
    nvd_json_id = Column(INTEGER(10), index=True)
    jvn_id = Column(INTEGER(10), index=True)
    source = Column(String(255))
    link = Column(Text)
    tags = Column(String(255))
