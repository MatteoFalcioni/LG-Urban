/**
 * AnimatedTitle: Smoothly animates text changes with a fluid transition.
 * Used for auto-titling updates to make them feel more natural.
 */

import { useState, useEffect, useRef } from 'react';

interface AnimatedTitleProps {
  title: string;
  className?: string;
  duration?: number; // Animation duration in milliseconds
}

export function AnimatedTitle({ title, className = '', duration = 400 }: AnimatedTitleProps) {
  const [displayedTitle, setDisplayedTitle] = useState(title);
  const [isAnimating, setIsAnimating] = useState(false);
  const previousTitleRef = useRef(title);
  const timeoutRef = useRef<number>();

  useEffect(() => {
    // Only animate if the title actually changed
    if (title !== previousTitleRef.current) {
      setIsAnimating(true);
      
      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      // Much faster animation - update immediately with shorter transition
      timeoutRef.current = setTimeout(() => {
        setDisplayedTitle(title);
        previousTitleRef.current = title;
        
        // End animation quickly
        setTimeout(() => {
          setIsAnimating(false);
        }, 50);
      }, duration / 3); // Much shorter delay
    }
  }, [title, duration]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <span 
      className={`transition-all ease-out ${
        isAnimating ? 'opacity-40 scale-98' : 'opacity-100 scale-100'
      } ${className}`}
      style={{
        transitionDuration: `${duration / 2}ms`,
        transform: isAnimating ? 'translateY(-1px)' : 'translateY(0px)',
      }}
    >
      {displayedTitle}
    </span>
  );
}
