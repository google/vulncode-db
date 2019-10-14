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

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    SubmitField,
    FieldList,
    FormField,
    IntegerField,
)
from wtforms import validators

from data.models import VulnerabilityGitCommits, VulnerabilityResources
from data.models.base import db


class ModelFieldList(FieldList):
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop("model", None)
        super(ModelFieldList, self).__init__(*args, **kwargs)
        if not self.model:
            raise ValueError("ModelFieldList requires model to be set")

    def populate_obj(self, obj, name):
        if not hasattr(obj, name):
            setattr(obj, name, [])
        while len(getattr(obj, name)) < len(self.entries):
            newModel = self.model()
            db.session.add(newModel)
            getattr(obj, name).append(newModel)
        while len(getattr(obj, name)) > len(self.entries):
            db.session.delete(getattr(obj, name).pop())
        super(ModelFieldList, self).populate_obj(obj, name)


class CommitLinksForm(FlaskForm):
    commit_link = StringField(
        "Commit Link",
        validators=[validators.DataRequired(),
                    validators.URL()])
    repo_name = StringField("Repository Name",
                            validators=[validators.DataRequired()])

    repo_url = StringField(
        "Git Repo URL", validators=[validators.Optional(),
                                    validators.URL()])
    commit_hash = StringField("Commit Hash", validators=[])

    class Meta:
        csrf = False


class VulnerabilityResourcesForm(FlaskForm):
    link = StringField(
        "Link", validators=[validators.DataRequired(),
                            validators.URL()])
    class Meta:
        csrf = False


class VulnerabilityDetailsForm(FlaskForm):
    commits = ModelFieldList(
        FormField(CommitLinksForm),
        model=VulnerabilityGitCommits,
        min_entries=1,
        default=[lambda: VulnerabilityGitCommits()],
    )

    # The filters argument is used to have Null fields instead of empty strings.
    # This is important since the cve_id is supposed to be unique OR Null.
    cve_id = StringField(
        "CVE-ID (if applicable)",
        filters=[lambda x: x and str(x).upper().strip(), lambda x: x or None],
        validators=[
            validators.Optional(),
            validators.Regexp(r"^CVE-\d{4}-\d+$")
        ],
    )
    comment = TextAreaField("High-Level Bug Overview",
                            validators=[validators.DataRequired()])
    additional_resources = ModelFieldList(
        FormField(VulnerabilityResourcesForm), model=VulnerabilityResources)
    submit = SubmitField("Create/Update")


class VulnerabilityDeleteForm(FlaskForm):
    delete_entry = IntegerField("Delete entry", [validators.required()])
    submit = SubmitField()
