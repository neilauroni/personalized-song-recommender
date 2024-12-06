import streamlit as st
import random
import json
from typing import Dict, List, Tuple

def initialize_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.update({
            'initialized': True,
            'feedback': [],
            'remaining_pairs': [],
            'current_pair_index': 0,
            'audio_files': {}
        })

def generate_pairs(file_names: List[str], existing_feedback: List[Dict] = None) -> List[Tuple[str, str]]:
    all_pairs = [(file_names[i], file_names[j])
                 for i in range(len(file_names))
                 for j in range(i + 1, len(file_names))]
    
    if existing_feedback:
        rated_pairs = {(f['song_a'], f['song_b']) for f in existing_feedback}
        rated_pairs.update({(f['song_b'], f['song_a']) for f in existing_feedback})
        
        remaining_pairs = [pair for pair in all_pairs 
                         if (pair[0], pair[1]) not in rated_pairs]
        return remaining_pairs
    
    return all_pairs

def save_uploaded_files(uploaded_files) -> Dict[str, bytes]:
    audio_files = {}
    for uploaded_file in uploaded_files:
        audio_files[uploaded_file.name] = uploaded_file.read()
    return audio_files

def handle_submission(similarity_score: float) -> bool:
    if st.session_state.remaining_pairs:
        current_pair = st.session_state.remaining_pairs[st.session_state.current_pair_index]
        feedback_entry = {
            'song_a': current_pair[0],
            'song_b': current_pair[1],
            'similarity_score': similarity_score
        }
        st.session_state.feedback.append(feedback_entry)
        st.session_state.current_pair_index += 1
        return True
    return False

def load_previous_feedback(feedback_file) -> List[Dict]:
    try:
        content = feedback_file.read()
        feedback_data = json.loads(content)
        
        if not isinstance(feedback_data, list):
            st.error("Invalid feedback file format: expected a list of ratings")
            return []
            
        for entry in feedback_data:
            if not all(key in entry for key in ['song_a', 'song_b', 'similarity_score']):
                st.error("Invalid feedback file format: missing required fields")
                return []
                
        return feedback_data
    except json.JSONDecodeError:
        st.error("Invalid JSON file")
        return []
    except Exception as e:
        st.error(f"Error loading feedback file: {str(e)}")
        return []

def main():
    st.set_page_config(page_title="Music Similarity Feedback App", layout="wide")
    st.title("Music Similarity Feedback Collection")
    
    initialize_session_state()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upload Audio Files")
        uploaded_files = st.file_uploader(
            "Upload WAV files",
            type="wav",
            accept_multiple_files=True,
            key="file_uploader"
        )
    
    with col2:
        st.subheader("Resume Previous Session")
        feedback_file = st.file_uploader(
            "Upload previous feedback JSON (optional)",
            type="json",
            key="feedback_uploader"
        )
    
    if uploaded_files:
        current_files = {f.name for f in uploaded_files}
        stored_files = set(st.session_state.audio_files.keys())
        
        if current_files != stored_files:
            st.session_state.audio_files = save_uploaded_files(uploaded_files)
            
            previous_feedback = []
            if feedback_file:
                previous_feedback = load_previous_feedback(feedback_file)
                if previous_feedback:
                    st.session_state.feedback = previous_feedback
                    st.success(f"Loaded {len(previous_feedback)} previous ratings")
            
            pairs = generate_pairs(
                list(st.session_state.audio_files.keys()),
                previous_feedback
            )
            random.shuffle(pairs)
            st.session_state.remaining_pairs = pairs
            st.session_state.current_pair_index = 0
            st.rerun()
        
        total_pairs = len(st.session_state.remaining_pairs) + len(st.session_state.feedback)
        rated_pairs = len(st.session_state.feedback)
        st.progress(rated_pairs / total_pairs if total_pairs > 0 else 0)
        st.write(f"Rated {rated_pairs} out of {total_pairs} pairs")
        
        if len(st.session_state.audio_files) < 2:
            st.warning("Please upload at least two WAV files to proceed.")
            return
        
        if (st.session_state.current_pair_index < 
            len(st.session_state.remaining_pairs)):
            
            current_pair = st.session_state.remaining_pairs[
                st.session_state.current_pair_index]
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Song 1: {current_pair[0]}**")
                st.audio(
                    st.session_state.audio_files[current_pair[0]],
                    format='audio/wav'
                )
            
            with col2:
                st.write(f"**Song 2: {current_pair[1]}**")
                st.audio(
                    st.session_state.audio_files[current_pair[1]],
                    format='audio/wav'
                )
            
            similarity_score = st.slider(
                "Rate the similarity between the two songs",
                min_value=0.0,
                max_value=1.0,
                value=0.5,  
                step=0.1,
                key=f"similarity_score_{st.session_state.current_pair_index}"
            )
            
            # Submit button
            if st.button("Submit Rating", key=f"submit_{st.session_state.current_pair_index}"):
                if handle_submission(similarity_score):
                    st.rerun()
        
        else:
            st.success("You have rated all possible pairs!")
        
        if st.session_state.feedback:
            feedback_json = json.dumps(st.session_state.feedback, indent=4)
            st.download_button(
                label='Download Feedback JSON',
                data=feedback_json,
                file_name='user_feedback.json',
                mime='application/json'
            )
        
        if st.button("Reset Session", key="reset_button"):
            if st.button("Confirm Reset", key="confirm_reset"):
                st.session_state.clear()
                st.rerun()
    
    else:
        st.write("Please upload WAV files to begin.")

if __name__ == "__main__":
    main()