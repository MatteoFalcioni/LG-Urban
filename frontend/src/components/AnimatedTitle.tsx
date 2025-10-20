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

export function AnimatedTitle({ title, className = '', duration = 800 }: AnimatedTitleProps) {
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

      // Start the animation sequence
      timeoutRef.current = setTimeout(() => {
        setDisplayedTitle(title);
        previousTitleRef.current = title;
        
        // End animation after a short delay
        setTimeout(() => {
          setIsAnimating(false);
        }, 100);
      }, duration / 2); // Half the duration for the fade out, half for fade in
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
      className={`transition-all duration-300 ease-in-out ${
        isAnimating ? 'opacity-30 scale-95' : 'opacity-100 scale-100'
      } ${className}`}
      style={{
        transitionDuration: `${duration / 2}ms`,
        transform: isAnimating ? 'translateY(-2px)' : 'translateY(0px)',
      }}
    >
      {displayedTitle}
    </span>
  );
}
