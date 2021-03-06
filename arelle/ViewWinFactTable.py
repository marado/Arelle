'''
Created on Nov 15, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from collections import defaultdict
import os, datetime
from tkinter import Menu, constants, BooleanVar
from arelle import ViewWinTree, ModelDtsObject, ModelInstanceObject, XbrlConst, XmlUtil

def viewFacts(modelXbrl, tabWin, header="Fact Table", arcrole=XbrlConst.parentChild, linkrole=None, linkqname=None, arcqname=None, lang=None):
    modelXbrl.modelManager.showStatus(_("viewing relationships {0}").format(os.path.basename(arcrole)))
    view = ViewFactTable(modelXbrl, tabWin, header, arcrole, linkrole, linkqname, arcqname, lang)
    view.ignoreDims = BooleanVar(value=False)
    view.showDimDefaults = BooleanVar(value=False)
    if view.view():
        view.treeView.bind("<<TreeviewSelect>>", view.treeviewSelect, '+')
        view.treeView.bind("<ButtonRelease-1>", view.treeviewClick, '+')
        view.treeView.bind("<Enter>", view.treeviewEnter, '+')
        view.treeView.bind("<Leave>", view.treeviewLeave, '+')

        # languages menu
        menu = view.contextMenu()
        optionsMenu = Menu(view.viewFrame, tearoff=0)
        view.ignoreDims.trace("w", view.viewReloadDueToMenuAction)
        optionsMenu.add_checkbutton(label=_("Ignore Dimensions"), underline=0, variable=view.ignoreDims, onvalue=True, offvalue=False)
        menu.add_cascade(label=_("Options"), menu=optionsMenu, underline=0)
        view.menuAddExpandCollapse()
        view.menuAddClipboard()
        view.menuAddLangs()
        view.menuAddLabelRoles(includeConceptName=True)
    
class ViewFactTable(ViewWinTree.ViewTree):
    def __init__(self, modelXbrl, tabWin, header, arcrole, linkrole=None, linkqname=None, arcqname=None, lang=None):
        super().__init__(modelXbrl, tabWin, header, True, lang)
        self.arcrole = arcrole
        self.linkrole = linkrole
        self.linkqname = linkqname
        self.arcqname = arcqname
        
    def viewReloadDueToMenuAction(self, *args):
        self.view()
        
    def view(self):
        self.blockSelectEvent = 1
        self.blockViewModelObject = 0
        self.tag_has = defaultdict(list) # temporary until Tk 8.6
        # relationship set based on linkrole parameter, to determine applicable linkroles
        relationshipSet = self.modelXbrl.relationshipSet(self.arcrole, self.linkrole, self.linkqname, self.arcqname)
        if not relationshipSet:
            self.modelXbrl.modelManager.addToLog(_("no relationships for {0}").format(self.arcrole))
            return False
        # set up facts
        self.conceptFacts = defaultdict(list)
        for fact in self.modelXbrl.facts:
            self.conceptFacts[fact.qname].append(fact)
        # sort contexts by period
        self.periodContexts = defaultdict(set)
        contextStartDatetimes = {}
        ignoreDims = self.ignoreDims.get()
        showDimDefaults = self.showDimDefaults.get()
        for context in self.modelXbrl.contexts.values():
            if ignoreDims:
                if context.isForeverPeriod:
                    contextkey = datetime.datetime(datetime.MINYEAR,1,1)
                else:
                    contextkey = context.endDatetime
            else:
                if context.isForeverPeriod:
                    contextkey = "forever"
                else:
                    contextkey = (context.endDatetime - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                
                values = []
                dims = context.qnameDims
                if len(dims) > 0:
                    for dimQname in sorted(dims.keys(), key=lambda d: str(d)):
                        dimvalue = dims[dimQname]
                        if dimvalue.isExplicit:
                            values.append(dimvalue.member.label(self.labelrole,lang=self.lang))
                        else:
                            values.append(XmlUtil.innerText(dimvalue.typedMember))
                            
                nonDimensions = context.nonDimValues("segment") + context.nonDimValues("scenario")
                if len(nonDimensions) > 0:
                    for element in sorted(nonDimensions, key=lambda e: e.localName):
                        values.append(XmlUtil.innerText(element))

                if len(values) > 0:
    
                    contextkey += " - " + ', '.join(values)

            objectId = context.objectId()
            self.periodContexts[contextkey].add(objectId)
            if context.isStartEndPeriod:
                contextStartDatetimes[objectId] = context.startDatetime
        self.periodKeys = list(self.periodContexts.keys())
        self.periodKeys.sort()
        # set up treeView widget and tabbed pane
        self.treeView.column("#0", width=300, anchor="w")
        self.treeView.heading("#0", text="Concept")
        columnIds = []
        columnIdHeadings = []
        self.contextColId = {}
        self.startdatetimeColId = {}
        self.numCols = 1
        for periodKey in self.periodKeys:
            colId = "#{0}".format(self.numCols)
            columnIds.append(colId)
            columnIdHeadings.append((colId,periodKey))
            for contextId in self.periodContexts[periodKey]:
                self.contextColId[contextId] = colId
                if contextId in contextStartDatetimes:
                    self.startdatetimeColId[contextStartDatetimes[contextId]] = colId
            self.numCols += 1
        self.treeView["columns"] = columnIds
        for colId, colHeading in columnIdHeadings:
            self.treeView.column(colId, width=60, anchor="w")
            if ignoreDims:
                if colHeading.year == datetime.MINYEAR:
                    date = "forever"
                else:
                    date = (colHeading - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                self.treeView.heading(colId, text=date)
            else:
                self.treeView.heading(colId, text=colHeading)

        # fact rendering
        for previousNode in self.treeView.get_children(""): 
            self.treeView.delete(previousNode)
        self.rowColFactId = {}
        # root node for tree view
        self.id = 1
        # sort URIs by definition
        linkroleUris = []
        relationshipSet = self.modelXbrl.relationshipSet(self.arcrole, self.linkrole, self.linkqname, self.arcqname)
        if self.linkrole:
            roleType = self.modelXbrl.roleTypes[self.linkrole]
            linkroleUris.append((self.linkrole, roleType.definition, roleType.objectId(self.id)))
            self.id += 1
        else:
            for linkroleUri in relationshipSet.linkRoleUris:
                modelRoleTypes = self.modelXbrl.roleTypes.get(linkroleUri)
                if modelRoleTypes is not None and len(modelRoleTypes) > 0:
                    roledefinition = modelRoleTypes[0].definition
                    if roledefinition is None or roledefinition == "":
                        roledefinition = linkroleUri                    
                    roleId = modelRoleTypes[0].objectId(self.id)
                else:
                    roledefinition = linkroleUri
                    roleId = "node{0}".format(self.id)
                self.id += 1
                linkroleUris.append((roledefinition, linkroleUri, roleId))
            linkroleUris.sort()
        # for each URI in definition order
        for linkroleUriTuple in linkroleUris:
            linknode = self.treeView.insert("", "end", linkroleUriTuple[2], text=linkroleUriTuple[0], tags=("ELR",))
            linkRelationshipSet = self.modelXbrl.relationshipSet(self.arcrole, linkroleUriTuple[1], self.linkqname, self.arcqname)
            for rootConcept in linkRelationshipSet.rootConcepts:
                node = self.viewConcept(rootConcept, rootConcept, "", self.labelrole, linknode, 1, linkRelationshipSet, set())
    
        return True

    def viewConcept(self, concept, modelObject, labelPrefix, preferredLabel, parentnode, n, relationshipSet, visited):
        if concept is None or concept.substitutionGroupQname == XbrlConst.qnXbrldtDimensionItem:
            return
        childnode = self.treeView.insert(parentnode, "end", modelObject.objectId(self.id),
                    text=labelPrefix + concept.label(preferredLabel,lang=self.lang), 
                    tags=("odd" if n & 1 else "even",))
        self.setRowFacts(childnode,concept,preferredLabel)
        self.id += 1
        self.tag_has[modelObject.objectId()].append(childnode)
        if isinstance(modelObject, ModelDtsObject.ModelRelationship):
            self.tag_has[modelObject.toModelObject.objectId()].append(childnode)
        if concept not in visited:
            visited.add(concept)
            for i, modelRel in enumerate(relationshipSet.fromModelObject(concept)):
                nestedRelationshipSet = relationshipSet
                targetRole = modelRel.targetRole
                if self.arcrole == XbrlConst.summationItem:
                    childPrefix = "({:0g}) ".format(modelRel.weight) # format without .0 on integer weights
                elif targetRole is None or len(targetRole) == 0:
                    targetRole = relationshipSet.linkrole
                    childPrefix = ""
                else:
                    nestedRelationshipSet = self.modelXbrl.relationshipSet(self.arcrole, targetRole, self.linkqname, self.arcqname)
                    childPrefix = "(via targetRole) "
                toConcept = modelRel.toModelObject
                if toConcept in visited:
                    childPrefix += "(loop)"
                labelrole = modelRel.preferredLabel
                if not labelrole: labelrole = self.labelrole
                self.viewConcept(toConcept, modelRel, childPrefix, labelrole, childnode, n + i + 1, nestedRelationshipSet, visited)
            visited.remove(concept)
            
    def setRowFacts(self, node, concept, preferredLabel):
        for fact in self.conceptFacts[concept.qname]:
            try:
                colId = self.contextColId[fact.context.objectId()]
                # special case of start date, pick column corresponding
                if preferredLabel == XbrlConst.periodStartLabel:
                    date = fact.context.instantDatetime
                    if date and date in self.startdatetimeColId:
                        colId = self.startdatetimeColId[date]
                self.treeView.set(node, 
                                  colId, 
                                  fact.effectiveValue)
                factObjectId = fact.objectId()
                self.tag_has[factObjectId].append(node)
                self.rowColFactId[node + colId] = factObjectId
            except AttributeError:  # not a fact or no concept
                pass
            
    def treeviewEnter(self, *args):
        self.blockSelectEvent = 0

    def treeviewLeave(self, *args):
        self.blockSelectEvent = 1

    def treeviewClick(self, event):
        if self.blockSelectEvent == 0 and self.blockViewModelObject == 0:
            self.blockViewModelObject += 1
            colId = self.treeView.identify_column(event.x)
            modelObjectId = self.treeView.identify_row(event.y)
            if colId != "" and modelObjectId != "":
                if colId == "#0":
                    self.modelXbrl.viewModelObject(modelObjectId)
                else:
                    factId = self.rowColFactId.get(modelObjectId + colId)
                    self.modelXbrl.viewModelObject(factId)
            self.blockViewModelObject -= 1
        
    def treeviewSelect(self, *args):
        if self.blockSelectEvent == 0 and self.blockViewModelObject == 0:
            self.blockViewModelObject += 1
            #self.modelXbrl.viewModelObject(self.treeView.selection()[0])
            self.blockViewModelObject -= 1
        
    def viewModelObject(self, modelObject):
        if self.blockViewModelObject == 0:
            self.blockViewModelObject += 1
            try:
                # get concept of fact or toConcept of relationship, role obj if roleType
                if not isinstance(modelObject, ModelInstanceObject.ModelFact):
                    modelObject = modelObject.viewConcept
                if modelObject is not None:
                    items = self.tag_has.get(modelObject.objectId())
                    if items is not None and self.treeView.exists(items[0]):
                        self.treeView.see(items[0])
                        self.treeView.selection_set(items[0])
            except (AttributeError, KeyError):
                self.treeView.selection_set(())
            self.blockViewModelObject -= 1

    