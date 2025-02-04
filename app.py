from flask import Flask, render_template, request, jsonify, send_from_directory
import spacy
import networkx as nx
import matplotlib.pyplot as plt
import os
 
app = Flask(__name__)
 
# Define a folder for saving the ERD image
UPLOAD_FOLDER = 'static/erd_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
 
global_relationships = []

# Load Spacy model
nlp = spacy.load("en_core_web_sm")

# Normalize entities for consistency
def normalize_entity(entity):
    return entity.lower().strip().rstrip("s")
 
# Remove redundant attributes
def remove_redundant_attributes(entities):
    all_entities = set(entities.keys())
    for entity, attributes in entities.items():
        entities[entity] = [
            attr for attr in attributes if normalize_entity(attr) not in all_entities
        ]
    return entities
 
# Function to extract entities and relationships from text
def extract_entities_and_relationships(text):
    #تحليل النص باستخدام ال spaCy
    doc = nlp(text)
    
    entities = {}
    current_entity = None
    relationships = []
    processed_tokens = set()  # Track tokens already processed as part of a compound attribute
    all_attributes = set()  # لتخزين كل الـ attributes
 
    for sent in doc.sents:#تقسيم النص الى جمل و معالجة كل جمله لحال 
        
        tokens = nlp(sent.text) #تقسيم الجمله الى كلمات ومعالجة كل كلمه لحال 
        entity = None
        for token in tokens:
            # استثناء كلمات محددة من الكيانات
            if token.text.lower() in ["system", "manages", "university", "time"]:
                continue  # تخطي هذه الكلمة وعدم إضافتها ككيان
 
            # Identify the main entity (noun or proper noun)
            if token.dep_ in ["nsubj", "ROOT", "pobj"] and token.pos_ in ["NOUN", "PROPN"]:
                entity = normalize_entity(token.text)
                if entity not in entities:
                    entities[entity] = []
                current_entity = entity
 
            # Collect attributes for the current entity
            elif (
                current_entity
                and token.dep_ in ["compound", "amod", "attr", "dobj", "conj"]
                and token.pos_ in ["NOUN", "PROPN", "ADJ"]
                and token not in processed_tokens
            ):
                attribute_tokens = [token]
                for left_token in reversed(list(token.lefts)):
                    if left_token.dep_ in ["compound", "amod"]:
                        attribute_tokens.insert(0, left_token)
                        processed_tokens.add(left_token)
                    else:
                        break
                combined_attr = " ".join(t.text for t in attribute_tokens).strip()
    
                # استثناء العبارات المركبة التي تحتوي على الكلمات المحددة
                if any(indicator in combined_attr.lower() for indicator in ["multiple", "many", "some"]):
                    processed_tokens.update(attribute_tokens)  # Mark tokens as processed
                    continue  # Skip this attribute
               
                # إضافة السمة إذا لم تكن موجودة بالفعل
                if combined_attr.lower() not in entities[current_entity]:
                    entities[current_entity].append(combined_attr)
                processed_tokens.update(attribute_tokens)
                all_attributes.add(combined_attr.lower())
 
            if token.text =="book":
                relation ="book"
                relationships.append((entity, relation, "flight"))
 
            # Handle relationships (prepositional phrases or verbs indicating actions)
            if token.pos_ == "VERB" and token.dep_ in ["ROOT", "relcl", "xcomp"]:
                target = None
                relation = token.lemma_
 
                # البحث عن المفعول به المباشر أو الكيانات المرتبطة
                for child in token.children:
                    if child.dep_ in ["dobj", "pobj"] and child.pos_ in ["NOUN", "PROPN"]:
                        target = normalize_entity(child.text)
                        break
                    elif child.dep_ == "prep":
                        for prep_child in child.children:
                            if prep_child.pos_ in ["NOUN", "PROPN"]:
                                target = normalize_entity(prep_child.text)
                                break
               
                if target:
                    relationships.append((entity, relation, target))
 
    # Post-process to remove duplicate or incomplete attributes
    for entity, attrs in entities.items():
        unique_attrs = []
        for attr in attrs:
            if not any(attr in other_attr and attr != other_attr for other_attr in attrs):
                unique_attrs.append(attr)
        entities[entity] = unique_attrs
 
    entities = remove_redundant_attributes(entities)
    return entities, relationships
 
# Function to generate SQL statements
# Generate SQL statements
def generate_sql(entities, relationships):
    sql_statements = []

    # Create tables for entities
    for entity, attrs in entities.items():
        sql = f"CREATE TABLE {entity} (\n"
        sql += " id INT AUTO_INCREMENT PRIMARY KEY,\n"
        for attr in attrs:
            sql += f" {attr.replace(' ', '_')} VARCHAR(255),\n"
        sql = sql.rstrip(",\n") + "\n);\n"
        sql_statements.append(sql)

    # Create relationship tables
    for source, rel, target in relationships:
        if source in entities and target in entities:
            sql = f"CREATE TABLE {source}_{target}_relation (\n"
            sql += f" {source}_id INT,\n"
            sql += f" {target}_id INT,\n"
            sql += f" PRIMARY KEY ({source}_id, {target}_id),\n"
            sql += f" FOREIGN KEY ({source}_id) REFERENCES {source}(id),\n"
            sql += f" FOREIGN KEY ({target}_id) REFERENCES {target}(id)\n);\n"
            sql_statements.append(sql)

    return sql_statements


def generate_erd(entities, relationships):

    global global_relationships  # Reference the global variable to store relationships
 
    # Store relationships in the global variable
    erd_relationships = []  # Relationships derived from the diagram
    global_relationships = relationships  # Store the original relationships globally
 
    G = nx.DiGraph()
 
    # Add entities and their attributes
    for entity, attrs in entities.items():
        G.add_node(entity, shape="rectangle", label=entity.capitalize())
        for attr in attrs:
            attr_name = f"{entity}_{attr}"
            G.add_node(attr_name, shape="circle", label=attr)
            G.add_edge(entity, attr_name)
 
    # Add relationships (only between entities)
    for source, rel, target in relationships:
        if target in entities and source in entities:  # Ensure relationships are between valid entities
            erd_relationships.append((source, rel, target))
            # Add source and target entities if not already present
            if source not in G:
                G.add_node(source, shape="rectangle", label=source.capitalize())
            if target not in G:
                G.add_node(target, shape="rectangle", label=target.capitalize())
           
            # Create a unique relationship node
            rel_name = f"{source}_{rel}_{target}"
            G.add_node(rel_name, shape="diamond", label=rel.capitalize())
           
            # Add edges to represent the relationship
            G.add_edge(source, rel_name)
            G.add_edge(rel_name, target)
 
    # Draw and save the ERD graph
    erd_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'erd_image.png')
    
    pos = nx.spring_layout(G, k=2)
    fig, ax = plt.subplots(figsize=(15, 10))
 
    # Separate nodes by type
    entity_nodes = [n for n, d in G.nodes(data=True) if d['shape'] == "rectangle"]
    attr_nodes = [n for n, d in G.nodes(data=True) if d['shape'] == "circle"]
    rel_nodes = [n for n, d in G.nodes(data=True) if d['shape'] == "diamond"]
 
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, nodelist=entity_nodes, node_shape="s", node_color="lightblue", label="Entities")
    nx.draw_networkx_nodes(G, pos, nodelist=attr_nodes, node_shape="o", node_color="lightgreen", label="Attributes")
    nx.draw_networkx_nodes(G, pos, nodelist=rel_nodes, node_shape="d", node_color="lightcoral", label="Relationships")
 
    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color="gray", arrows=True)
 
    # Draw labels
    nx.draw_networkx_labels(G, pos, labels={n: d.get('label', n) for n, d in G.nodes(data=True)}, font_size=10)
 
    # Add legend and title
    plt.legend(scatterpoints=1)
    plt.title("Entity-Relationship Diagram (ERD)")
    plt.savefig(erd_image_path)  # Save the image
    plt.close(fig)  # Close the plot to free memory
 
    return erd_relationships, 'erd_image.png'
 
# Route to serve the index page
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process_scenario', methods=['POST'])
def process_scenario():
    scenario = request.json.get('scenario')
    entities, relationships = extract_entities_and_relationships(scenario)
     # Generate ERD and SQL
    extracted_relationships, erd_image_path = generate_erd(entities, relationships)
    sql_statements = generate_sql(entities, relationships)
 
    # Prepare response data
    response_data = {
        'entities': entities,  # Send entities with attributes
        'relationships': extracted_relationships,
        'erd_image_path': erd_image_path,  # Path to the ERD image
        'sql_statements': sql_statements  # SQL statements
    }
 
    return jsonify(response_data)
 
 
if __name__ == '__main__':
    app.run(debug=True)
 
 