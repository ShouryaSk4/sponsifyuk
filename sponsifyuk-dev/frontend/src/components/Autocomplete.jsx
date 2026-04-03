import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const Autocomplete = ({ value, onChange, placeholder, iconClass, type }) => {
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const wrapperRef = useRef(null);

    // Debounce timer ref
    const debounceTimer = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
                setShowSuggestions(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const fetchSuggestions = (query) => {
        if (query.length < 2) {
            setSuggestions([]);
            return;
        }
        
        axios.get(`${API_URL}/jobs/suggestions`, {
            params: { q: query, type: type }
        })
        .then(res => {
            setSuggestions(res.data || []);
        })
        .catch(err => {
            console.error("Error fetching suggestions:", err);
            setSuggestions([]);
        });
    };

    const handleInputChange = (e) => {
        const val = e.target.value;
        onChange(val);
        
        if (val.length >= 2) {
            setShowSuggestions(true);
            
            // Debounce the API call
            if (debounceTimer.current) clearTimeout(debounceTimer.current);
            debounceTimer.current = setTimeout(() => {
                fetchSuggestions(val);
            }, 300);
        } else {
            setShowSuggestions(false);
            setSuggestions([]);
        }
    };

    const handleSuggestionClick = (suggestion) => {
        onChange(suggestion);
        setShowSuggestions(false);
    };

    return (
        <div className="form-group position-relative" ref={wrapperRef}>
            <input 
                className="form-control" 
                type="text" 
                placeholder={placeholder} 
                value={value}
                onChange={handleInputChange}
                onFocus={() => { if (value.length >= 2 && suggestions.length > 0) setShowSuggestions(true); }}
                autoComplete="off"
            />
            {iconClass && <i className={iconClass}></i>}
            
            {showSuggestions && suggestions.length > 0 && (
                <div className="autocomplete-suggestions" style={{ display: 'block' }}>
                    {suggestions.map((suggestion, index) => (
                        <div 
                            key={index} 
                            className="suggestion-item" 
                            onClick={() => handleSuggestionClick(suggestion)}
                        >
                            {suggestion}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default Autocomplete;
